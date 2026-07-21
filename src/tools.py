import os
import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

# Supported file extensions for static analysis
CODE_EXTENSIONS: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "React/TSX",
    ".jsx": "React/JSX",
    ".go": "Go",
    ".java": "Java",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
    ".html": "HTML",
    ".css": "CSS",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".md": "Markdown",
    ".sql": "SQL",
    ".sh": "Shell"
}

IGNORE_DIRS = {".git", ".venv", "node_modules", "__pycache__", "dist", "build", ".idea", ".vscode"}

def scan_directory_structure(root_dir: str) -> Dict[str, Any]:
    """Scans repository directory structure and returns file tree and language breakdown.

    Args:
        root_dir (str): Absolute or relative file path to the repository directory to scan.

    Returns:
        Dict[str, Any]: Dictionary containing root path, total file count, total dir count,
            language breakdown dictionary, and sample file list.
    """
    root_path = Path(root_dir).resolve()
    if not root_path.exists():
        return {"error": f"Path '{root_dir}' does not exist"}

    file_tree: List[str] = []
    extension_counts: Dict[str, int] = {}
    total_files: int = 0
    total_dirs: int = 0

    for current_root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        
        rel_path = os.path.relpath(current_root, root_path)
        if rel_path == ".":
            rel_path = ""
            
        total_dirs += len(dirs)

        for file in files:
            if file.startswith("."):
                continue
            total_files += 1
            ext = Path(file).suffix.lower()
            lang = CODE_EXTENSIONS.get(ext, "Other")
            extension_counts[lang] = extension_counts.get(lang, 0) + 1
            
            file_rel_path = os.path.join(rel_path, file) if rel_path else file
            if len(file_tree) < 100:
                file_tree.append(file_rel_path)

    return {
        "root": str(root_path),
        "total_files": total_files,
        "total_dirs": total_dirs,
        "language_breakdown": extension_counts,
        "file_list_sample": file_tree
    }

def analyze_code_metrics(root_dir: str) -> Dict[str, Any]:
    """Calculates lines of code (LOC), comments, and blank lines across supported files.

    Args:
        root_dir (str): Absolute or relative file path to the repository directory to analyze.

    Returns:
        Dict[str, Any]: Dictionary containing total LOC, code lines, comment lines, blank lines,
            comment ratio percentage, and top largest files sorted by LOC.
    """
    root_path = Path(root_dir).resolve()
    total_loc: int = 0
    total_code: int = 0
    total_comments: int = 0
    total_blank: int = 0
    file_metrics: List[Dict[str, Any]] = []

    for current_root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

        for file in files:
            ext = Path(file).suffix.lower()
            if ext not in CODE_EXTENSIONS:
                continue

            file_path = os.path.join(current_root, file)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    
                loc = len(lines)
                blank = 0
                comments = 0
                code = 0

                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        blank += 1
                    elif stripped.startswith(("#", "//", "/*", "*", '"""', "'''")):
                        comments += 1
                    else:
                        code += 1

                total_loc += loc
                total_code += code
                total_comments += comments
                total_blank += blank

                file_metrics.append({
                    "file": os.path.relpath(file_path, root_path),
                    "total_loc": loc,
                    "code_loc": code,
                    "comment_loc": comments,
                    "language": CODE_EXTENSIONS.get(ext, "Other")
                })
            except Exception:
                continue

    file_metrics.sort(key=lambda x: x["total_loc"], reverse=True)

    return {
        "summary": {
            "total_loc": total_loc,
            "total_code": total_code,
            "total_comments": total_comments,
            "total_blank": total_blank,
            "comment_ratio_pct": round((total_comments / max(1, total_code)) * 100, 2)
        },
        "top_largest_files": file_metrics[:15]
    }

def extract_imports_and_deps(root_dir: str) -> Dict[str, Any]:
    """Parses package manifests and code imports to build dependency maps.

    Args:
        root_dir (str): Absolute or relative file path to the repository directory to inspect.

    Returns:
        Dict[str, Any]: Dictionary containing manifest dependencies, external libraries set,
            and file dependency maps.
    """
    root_path = Path(root_dir).resolve()
    manifest_deps: List[str] = []
    internal_imports: Dict[str, List[str]] = {}
    external_imports: set = set()

    req_file = root_path / "requirements.txt"
    if req_file.exists():
        try:
            with open(req_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        manifest_deps.append(line.split("==")[0].split(">=")[0].strip())
        except Exception:
            pass

    pkg_file = root_path / "package.json"
    if pkg_file.exists():
        try:
            with open(pkg_file, "r") as f:
                data = json.load(f)
                deps = data.get("dependencies", {})
                dev_deps = data.get("devDependencies", {})
                manifest_deps.extend(list(deps.keys()) + list(dev_deps.keys()))
        except Exception:
            pass

    for current_root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(current_root, file)
                rel_path = os.path.relpath(file_path, root_path)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read(), filename=file_path)

                    file_imports: List[str] = []
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                file_imports.append(alias.name)
                                external_imports.add(alias.name.split(".")[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                file_imports.append(node.module)
                                external_imports.add(node.module.split(".")[0])
                    internal_imports[rel_path] = file_imports
                except Exception:
                    continue

    return {
        "manifest_dependencies": manifest_deps,
        "external_libraries": list(external_imports)[:30],
        "file_dependency_map": internal_imports
    }

def detect_api_routes(root_dir: str) -> List[Dict[str, str]]:
    """Detects API routes and endpoints in Python (FastAPI/Flask) or JS/TS (Express/Next).

    Args:
        root_dir (str): Absolute or relative file path to the repository directory to scan.

    Returns:
        List[Dict[str, str]]: List of route dictionaries containing HTTP method, endpoint path,
            file location, and framework type.
    """
    root_path = Path(root_dir).resolve()
    routes: List[Dict[str, str]] = []
    
    route_patterns = [
        (r'@(?:app|router|api)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', "Python (FastAPI/Flask)"),
        (r'(?:app|router)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', "Node.js (Express)"),
    ]

    for current_root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in [".py", ".js", ".ts", ".jsx", ".tsx"]:
                file_path = os.path.join(current_root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    
                    for pattern, framework in route_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        for method, endpoint in matches:
                            route_entry = {
                                "method": method.upper(),
                                "endpoint": endpoint,
                                "file": os.path.relpath(file_path, root_path),
                                "framework": framework
                            }
                            if route_entry not in routes:
                                routes.append(route_entry)
                except Exception:
                    continue

    return routes

def scan_security_and_secrets(root_dir: str) -> List[Dict[str, str]]:
    """Scans for potential hardcoded secrets, dangerous calls, or security anti-patterns.

    Args:
        root_dir (str): Absolute or relative file path to the repository directory to audit.

    Returns:
        List[Dict[str, str]]: List of security finding dictionaries containing file path, line number,
            risk classification, and line snippet.
    """
    root_path = Path(root_dir).resolve()
    findings: List[Dict[str, str]] = []

    secret_patterns = [
        (r'(?i)(api_key|apikey|secret|token|password)\s*=\s*["\'][A-Za-z0-9_\-]{8,}["\']', "Potential Hardcoded Secret"),
        (r'eval\(', "Dangerous Dynamic Execution (eval)"),
        (r'exec\(', "Dangerous Dynamic Execution (exec)"),
        (r'subprocess\.run\(.*shell\s*=\s*True', "Shell Injection Risk (shell=True)"),
        (r'os\.system\(', "Command Injection Risk (os.system)")
    ]

    for current_root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in CODE_EXTENSIONS and file not in ["tools.py"]:
                file_path = os.path.join(current_root, file)
                rel_path = os.path.relpath(file_path, root_path)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    
                    for idx, line in enumerate(lines, 1):
                        for pattern, risk_name in secret_patterns:
                            if re.search(pattern, line):
                                findings.append({
                                    "file": rel_path,
                                    "line": idx,
                                    "risk": risk_name,
                                    "snippet": line.strip()[:60]
                                })
                except Exception:
                    continue

    return findings

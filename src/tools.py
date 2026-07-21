import os
import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Any

# Supported file extensions for analysis
CODE_EXTENSIONS = {
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
    """Scans repository directory structure and returns file tree and language breakdown."""
    root_path = Path(root_dir).resolve()
    if not root_path.exists():
        return {"error": f"Path '{root_dir}' does not exist"}

    file_tree = []
    extension_counts = {}
    total_files = 0
    total_dirs = 0

    for current_root, dirs, files in os.walk(root_path):
        # Filter ignored directories in-place
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
            if len(file_tree) < 100:  # Cap file tree representation for prompt efficiency
                file_tree.append(file_rel_path)

    return {
        "root": str(root_path),
        "total_files": total_files,
        "total_dirs": total_dirs,
        "language_breakdown": extension_counts,
        "file_list_sample": file_tree
    }

def analyze_code_metrics(root_dir: str) -> Dict[str, Any]:
    """Calculates lines of code (LOC), comments, and blank lines across supported files."""
    root_path = Path(root_dir).resolve()
    total_loc = 0
    total_code = 0
    total_comments = 0
    total_blank = 0
    file_metrics = []

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

    # Sort files by LOC descending
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
    """Parses package manifests and code imports to build dependency maps."""
    root_path = Path(root_dir).resolve()
    manifest_deps = []
    internal_imports = {}
    external_imports = set()

    # Parse Python requirements.txt or pyproject.toml
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

    # AST Parsing for Python files
    for current_root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(current_root, file)
                rel_path = os.path.relpath(file_path, root_path)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read(), filename=file_path)

                    file_imports = []
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
    """Detects API routes and endpoints in Python (FastAPI/Flask) or JS/TS (Express/Next)."""
    root_path = Path(root_dir).resolve()
    routes = []
    
    route_patterns = [
        # FastAPI / Flask patterns
        (r'@(?:app|router|api)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', "Python (FastAPI/Flask)"),
        # Express.js patterns
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
                            routes.append({
                                "method": method.upper(),
                                "endpoint": endpoint,
                                "file": os.path.relpath(file_path, root_path),
                                "framework": framework
                            })
                except Exception:
                    continue

    return routes

def scan_security_and_secrets(root_dir: str) -> List[Dict[str, str]]:
    """Scans for potential hardcoded secrets, dangerous calls, or security anti-patterns."""
    root_path = Path(root_dir).resolve()
    findings = []

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
            if ext in CODE_EXTENSIONS and file not in ["tools.py"]:  # Exclude self patterns
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

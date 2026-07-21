import sys
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.tools import (
    scan_directory_structure,
    analyze_code_metrics,
    extract_imports_and_deps,
    detect_api_routes,
    scan_security_and_secrets
)

__all__ = [
    "scan_directory_structure",
    "analyze_code_metrics",
    "extract_imports_and_deps",
    "detect_api_routes",
    "scan_security_and_secrets"
]

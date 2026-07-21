import pytest
from pathlib import Path
from src.tools import (
    scan_directory_structure,
    analyze_code_metrics,
    extract_imports_and_deps,
    detect_api_routes,
    scan_security_and_secrets
)

def test_scan_directory_structure(tmp_path):
    (tmp_path / "test.py").write_text("print('hello')")
    res = scan_directory_structure(str(tmp_path))
    assert res["total_files"] == 1
    assert "Python" in res["language_breakdown"]

def test_analyze_code_metrics(tmp_path):
    code_file = tmp_path / "app.py"
    code_file.write_text("# Comment\nx = 1\ny = 2\n")
    res = analyze_code_metrics(str(tmp_path))
    assert res["summary"]["total_loc"] == 3
    assert res["summary"]["total_code"] == 2
    assert res["summary"]["total_comments"] == 1

def test_extract_imports_and_deps(tmp_path):
    code_file = tmp_path / "main.py"
    code_file.write_text("import os\nfrom math import sqrt\n")
    res = extract_imports_and_deps(str(tmp_path))
    assert "os" in res["external_libraries"] or "math" in res["external_libraries"]

def test_detect_api_routes(tmp_path):
    server_file = tmp_path / "server.py"
    server_file.write_text('@app.get("/api/v1/test")\ndef test(): pass\n')
    routes = detect_api_routes(str(tmp_path))
    assert len(routes) >= 1
    assert routes[0]["endpoint"] == "/api/v1/test"

def test_scan_security_and_secrets(tmp_path):
    sec_file = tmp_path / "config.py"
    sec_file.write_text('API_KEY = "secret12345678"\n')
    findings = scan_security_and_secrets(str(tmp_path))
    assert len(findings) >= 1
    assert findings[0]["risk"] == "Potential Hardcoded Secret"

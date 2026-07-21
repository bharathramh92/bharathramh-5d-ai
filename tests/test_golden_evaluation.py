import json
import pytest
from pathlib import Path
from src.agent import MultiAgentCodeArchSystem

def test_golden_dataset_evaluations(tmp_path):
    golden_path = Path(__file__).resolve().parent / "golden_dataset.json"
    with open(golden_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    agent = MultiAgentCodeArchSystem(session_id="golden_eval")

    for case in cases:
        case_dir = tmp_path / case["id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        
        for fname, fcontent in case["files"].items():
            (case_dir / fname).write_text(fcontent)

        report = agent.run_full_analysis(str(case_dir))
        assert report["status"] == "SUCCESS"

        if "expected_files_count" in case:
            assert report["inspection_summary"]["total_files"] == case["expected_files_count"]

        if "expected_loc" in case:
            assert report["inspection_summary"]["total_loc"] == case["expected_loc"]

        if "expected_routes_count" in case:
            assert report["inspection_summary"]["api_route_count"] >= case["expected_routes_count"]

        if "expected_security_findings_count" in case:
            assert report["inspection_summary"]["security_findings_count"] >= case["expected_security_findings_count"]

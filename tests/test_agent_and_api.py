import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from src.agent import MultiAgentCodeArchSystem
from src.server import app

client = TestClient(app)

def test_api_status():
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"

def test_api_analyze_fallback(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')\n")
    response = client.post("/api/analyze", json={"target_dir": str(tmp_path)})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "diagrams" in data
    assert "security_report" in data
    assert "documentation" in data

def test_api_telemetry_and_memory(tmp_path):
    (tmp_path / "app.py").write_text("x = 10\n")
    agent = MultiAgentCodeArchSystem(session_id="test_session")
    report = agent.run_full_analysis(str(tmp_path))
    assert report["status"] == "SUCCESS"

    tel_resp = client.get("/api/telemetry")
    assert tel_resp.status_code == 200
    assert tel_resp.json()["total_spans"] > 0

    mem_resp = client.get("/api/memory?session_id=test_session")
    assert mem_resp.status_code == 200
    assert mem_resp.json()["latest_report"] is not None

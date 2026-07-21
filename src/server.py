import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import MultiAgentCodeArchSystem

app = FastAPI(
    title="ArchAgent - Codebase & Technical Architecture Multi-Agent AI System",
    description="Automated multi-agent codebase analysis, Mermaid diagram synthesis, ADR generation, and interactive architecture Q&A.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory cache of latest report
LATEST_REPORT: Dict[str, Any] = {}

class AnalyzeRequest(BaseModel):
    target_dir: Optional[str] = None

class ChatRequest(BaseModel):
    question: str
    report_context: Optional[Dict[str, Any]] = None

@app.get("/api/status")
def status():
    api_key_set = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "online",
        "system": "ArchAgent Multi-Agent Engine",
        "gemini_api_key_configured": api_key_set
    }

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    global LATEST_REPORT
    target_dir = req.target_dir or str(Path(__file__).resolve().parent.parent)
    
    if not os.path.exists(target_dir):
        raise HTTPException(status_code=400, detail=f"Directory '{target_dir}' does not exist.")

    try:
        agent_system = MultiAgentCodeArchSystem()
        report = agent_system.run_full_analysis(target_dir)
        LATEST_REPORT = report
        return JSONResponse(content=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
def chat(req: ChatRequest):
    global LATEST_REPORT
    report = req.report_context or LATEST_REPORT
    if not report:
        raise HTTPException(status_code=400, detail="No active analysis report context found. Run an analysis first.")

    try:
        agent_system = MultiAgentCodeArchSystem()
        answer = agent_system.answer_architecture_question(req.question, report)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static directory for frontend UI
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse)
def root():
    index_path = static_dir / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>ArchAgent Backend Online</h1><p>Frontend static files not found.</p>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.server:app", host="0.0.0.0", port=8000, reload=True)

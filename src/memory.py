import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

class SessionMemoryManager:
    """Persistent Context & Memory Manager for ArchAgent."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else Path(__file__).resolve().parent.parent / ".memory"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.storage_dir / "sessions.json"
        self.sessions: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.sessions, f, indent=2)
        except Exception:
            pass

    def get_or_create_session(self, session_id: str = "default") -> Dict[str, Any]:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "created_at": time.time(),
                "history": [],
                "latest_report": None,
                "context_window_size": 20
            }
            self._save()
        return self.sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        session = self.get_or_create_session(session_id)
        msg = {
            "timestamp": time.time(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        session["history"].append(msg)
        # Apply sliding context window limit
        if len(session["history"]) > session.get("context_window_size", 20):
            session["history"] = session["history"][-session.get("context_window_size", 20):]
        self._save()

    def save_report(self, session_id: str, report: Dict[str, Any]):
        session = self.get_or_create_session(session_id)
        session["latest_report"] = report
        self._save()

    def get_latest_report(self, session_id: str = "default") -> Optional[Dict[str, Any]]:
        session = self.get_or_create_session(session_id)
        return session.get("latest_report")

    def get_history(self, session_id: str = "default") -> List[Dict[str, Any]]:
        session = self.get_or_create_session(session_id)
        return session.get("history", [])

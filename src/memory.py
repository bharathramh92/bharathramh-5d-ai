import sqlite3
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

class SessionMemoryManager:
    """Async-capable SQLite Session & Context Memory Manager with Summarization Compaction."""

    def __init__(self, db_dir: Optional[str] = None):
        self.storage_dir = Path(db_dir) if db_dir else Path(__file__).resolve().parent.parent / ".memory"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_dir / "sessions.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at REAL,
                    latest_report TEXT,
                    summary TEXT,
                    context_window_size INTEGER DEFAULT 20
                )
            """)
            # Schema migration check for summary column
            try:
                conn.execute("ALTER TABLE sessions ADD COLUMN summary TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    metadata TEXT,
                    timestamp REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.commit()

    def get_or_create_session(self, session_id: str = "default") -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id, created_at, latest_report, summary, context_window_size FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                created_at = time.time()
                cursor.execute("INSERT INTO sessions (session_id, created_at, latest_report, summary, context_window_size) VALUES (?, ?, ?, ?, ?)",
                               (session_id, created_at, None, None, 20))
                conn.commit()
                return {"session_id": session_id, "created_at": created_at, "latest_report": None, "summary": None, "context_window_size": 20}
            
            report = json.loads(row[2]) if row[2] else None
            return {"session_id": row[0], "created_at": row[1], "latest_report": report, "summary": row[3], "context_window_size": row[4]}

    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.get_or_create_session(session_id)
        meta_str = json.dumps(metadata or {})
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, metadata, timestamp) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, meta_str, time.time())
            )
            conn.commit()
        self._check_and_summarize(session_id)

    async def add_message_async(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        await asyncio.to_thread(self.add_message, session_id, role, content, metadata)

    def _check_and_summarize(self, session_id: str):
        """Summarizes older conversation turns when count exceeds context threshold."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,))
            count = cursor.fetchone()[0]
            if count > 10:
                cursor.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC LIMIT 5", (session_id,))
                rows = cursor.fetchall()
                summary_text = f"Historical Conversation Summary ({len(rows)} turns compacted):\n" + "\n".join([f"{r[0]}: {r[1][:100]}" for r in rows])
                cursor.execute("UPDATE sessions SET summary = ? WHERE session_id = ?", (summary_text, session_id))
                conn.commit()

    def save_report(self, session_id: str, report: Dict[str, Any]):
        self.get_or_create_session(session_id)
        report_str = json.dumps(report)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE sessions SET latest_report = ? WHERE session_id = ?", (report_str, session_id))
            conn.commit()

    async def save_report_async(self, session_id: str, report: Dict[str, Any]):
        await asyncio.to_thread(self.save_report, session_id, report)

    def get_latest_report(self, session_id: str = "default") -> Optional[Dict[str, Any]]:
        session = self.get_or_create_session(session_id)
        return session.get("latest_report")

    def get_history(self, session_id: str = "default") -> List[Dict[str, Any]]:
        session = self.get_or_create_session(session_id)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content, metadata, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT 20",
                (session_id,)
            )
            rows = cursor.fetchall()
            history = []
            if session.get("summary"):
                history.append({"role": "system", "content": session["summary"], "metadata": {"is_summary": True}, "timestamp": time.time()})

            for row in reversed(rows):
                history.append({
                    "role": row[0],
                    "content": row[1],
                    "metadata": json.loads(row[2]) if row[2] else {},
                    "timestamp": row[3]
                })
            return history

    async def get_history_async(self, session_id: str = "default") -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self.get_history, session_id)

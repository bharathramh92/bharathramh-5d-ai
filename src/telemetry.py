import time
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

class TelemetryTracer:
    """Observability & Tracing Engine for Agent Execution Telemetry."""

    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).resolve().parent.parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.log_dir / "trace.json"
        self.spans: List[Dict[str, Any]] = []

    def start_span(self, name: str, agent_name: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        span = {
            "span_id": f"span_{len(self.spans) + 1}",
            "name": name,
            "agent": agent_name,
            "start_time": time.time(),
            "status": "IN_PROGRESS",
            "metadata": meta or {}
        }
        self.spans.append(span)
        return span

    def end_span(self, span: Dict[str, Any], status: str = "SUCCESS", output: Optional[Any] = None, error: Optional[str] = None):
        span["end_time"] = time.time()
        span["duration_ms"] = round((span["end_time"] - span["start_time"]) * 1000, 2)
        span["status"] = status
        if output:
            span["output_summary"] = str(output)[:200]
        if error:
            span["error"] = error
        self._flush()

    def _flush(self):
        try:
            with open(self.trace_file, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": time.time(),
                    "total_spans": len(self.spans),
                    "spans": self.spans
                }, f, indent=2)
        except Exception:
            pass

    def get_trace_summary(self) -> Dict[str, Any]:
        return {
            "total_spans": len(self.spans),
            "trace_file": str(self.trace_file),
            "spans": self.spans
        }

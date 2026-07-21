import time
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configure structured JSON logger
logger = logging.getLogger("ArchAgentTelemetry")
logger.setLevel(logging.INFO)

def redact_pii(text: str) -> str:
    """Scrubs sensitive credentials, API keys, tokens, emails, and passwords from text strings."""
    if not isinstance(text, str):
        return text
    # Redact Gemini / GCP / AWS API keys
    text = re.sub(r'(?i)(api_key|token|password|secret)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{8,}["\']?', r'\1=***REDACTED***', text)
    text = re.sub(r'AIzaSy[A-Za-z0-9_\-]{33}', '***REDACTED_GEMINI_KEY***', text)
    # Redact Email addresses
    text = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '***REDACTED_EMAIL***', text)
    return text

class TelemetryTracer:
    """OpenTelemetry-compatible Tracing Engine with PII Redaction and Structured Logging."""

    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).resolve().parent.parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.log_dir / "trace.json"
        self.spans: List[Dict[str, Any]] = []

    def start_span(self, name: str, agent_name: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        sanitized_meta = {k: redact_pii(str(v)) for k, v in (meta or {}).items()}
        span = {
            "trace_id": "0x4bf92f3577b34da6a3ce929d0e0e4736",
            "span_id": f"span_{len(self.spans) + 1}",
            "name": name,
            "agent": agent_name,
            "start_time": time.time(),
            "status": "IN_PROGRESS",
            "metadata": sanitized_meta
        }
        self.spans.append(span)
        logger.info(json.dumps({"event": "SPAN_START", "span_id": span["span_id"], "name": name, "agent": agent_name}))
        return span

    def end_span(self, span: Dict[str, Any], status: str = "SUCCESS", output: Optional[Any] = None, error: Optional[str] = None):
        span["end_time"] = time.time()
        span["duration_ms"] = round((span["end_time"] - span["start_time"]) * 1000, 2)
        span["status"] = status
        if output:
            span["output_summary"] = redact_pii(str(output)[:200])
        if error:
            span["error"] = redact_pii(str(error))
        
        logger.info(json.dumps({
            "event": "SPAN_END",
            "span_id": span["span_id"],
            "duration_ms": span["duration_ms"],
            "status": status
        }))
        self._flush()

    def _flush(self):
        try:
            with open(self.trace_file, "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": "1.0",
                    "telemetry_format": "opentelemetry-compatible",
                    "pii_redaction": "enabled",
                    "timestamp": time.time(),
                    "total_spans": len(self.spans),
                    "spans": self.spans
                }, f, indent=2)
        except Exception:
            pass

    def get_trace_summary(self) -> Dict[str, Any]:
        return {
            "telemetry_format": "opentelemetry-compatible",
            "pii_redaction": "enabled",
            "total_spans": len(self.spans),
            "trace_file": str(self.trace_file),
            "spans": self.spans
        }

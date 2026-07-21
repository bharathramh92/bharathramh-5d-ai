import time
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

# Initialize OpenTelemetry TracerProvider
provider = TracerProvider()
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
otel_tracer = trace.get_tracer("ArchAgentTracer")

logger = logging.getLogger("ArchAgentTelemetry")
logger.setLevel(logging.INFO)

def redact_pii(text: str) -> str:
    """Redacts PII using Cloud DLP API with regex fallback."""
    if not isinstance(text, str):
        return text

    # Attempt Google Cloud DLP API PII Inspection
    try:
        from google.cloud import dlp_v2
        dlp = dlp_v2.DlpServiceClient()
        project_id = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        if project_id:
            parent = f"projects/{project_id}"
            item = {"value": text}
            inspect_config = {
                "info_types": [{"name": "EMAIL_ADDRESS"}, {"name": "SECRET_KEY"}, {"name": "AUTH_TOKEN"}],
                "min_likelihood": dlp_v2.Likelihood.POSSIBLE,
            }
            deidentify_config = {
                "info_type_transformations": {
                    "transformations": [{
                        "primitive_transformation": {
                            "replace_with_info_type_config": {}
                        }
                    }]
                }
            }
            response = dlp.deidentify_content(
                request={"parent": parent, "deidentify_config": deidentify_config, "inspect_config": inspect_config, "item": item}
            )
            text = response.item.value
    except Exception:
        pass

    # Regex Fallback Redaction
    text = re.sub(r'(?i)(api_key|token|password|secret)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{8,}["\']?', r'\1=***REDACTED***', text)
    text = re.sub(r'AIzaSy[A-Za-z0-9_\-]{33}', '***REDACTED_GEMINI_KEY***', text)
    text = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '***REDACTED_EMAIL***', text)
    return text

class TelemetryTracer:
    """Distributed Tracing Engine using OpenTelemetry Library and Cloud DLP Redaction."""

    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).resolve().parent.parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.log_dir / "trace.json"
        self.spans: List[Dict[str, Any]] = []

    def start_span(self, name: str, agent_name: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        sanitized_meta = {k: redact_pii(str(v)) for k, v in (meta or {}).items()}
        
        # OpenTelemetry span invocation
        otel_span = otel_tracer.start_span(name)
        trace_id = hex(otel_span.get_span_context().trace_id) if otel_span.get_span_context().trace_id else f"0x{uuid.uuid4().hex}"
        span_id = hex(otel_span.get_span_context().span_id) if otel_span.get_span_context().span_id else f"0x{uuid.uuid4().hex[:16]}"
        
        span = {
            "trace_id": trace_id,
            "span_id": span_id,
            "name": name,
            "agent": agent_name,
            "start_time": time.time(),
            "status": "IN_PROGRESS",
            "metadata": sanitized_meta,
            "_otel_span": otel_span
        }
        self.spans.append(span)
        logger.info(json.dumps({"event": "SPAN_START", "trace_id": trace_id, "span_id": span_id, "name": name, "agent": agent_name}))
        return span

    def end_span(self, span: Dict[str, Any], status: str = "SUCCESS", output: Optional[Any] = None, error: Optional[str] = None):
        span["end_time"] = time.time()
        span["duration_ms"] = round((span["end_time"] - span["start_time"]) * 1000, 2)
        span["status"] = status
        if output:
            span["output_summary"] = redact_pii(str(output)[:200])
        if error:
            span["error"] = redact_pii(str(error))
        
        if "_otel_span" in span and span["_otel_span"]:
            try:
                span["_otel_span"].end()
            except Exception:
                pass
            del span["_otel_span"]

        logger.info(json.dumps({
            "event": "SPAN_END",
            "span_id": span["span_id"],
            "duration_ms": span["duration_ms"],
            "status": status
        }))
        self._flush()

    def _flush(self):
        try:
            clean_spans = [
                {k: v for k, v in span.items() if k != "_otel_span"}
                for span in self.spans
            ]
            with open(self.trace_file, "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": "1.0",
                    "telemetry_format": "opentelemetry-sdk",
                    "pii_redaction": "enabled (Cloud DLP + Regex)",
                    "timestamp": time.time(),
                    "total_spans": len(clean_spans),
                    "spans": clean_spans
                }, f, indent=2)
        except Exception:
            pass

    def get_trace_summary(self) -> Dict[str, Any]:
        clean_spans = [
            {k: v for k, v in span.items() if k != "_otel_span"}
            for span in self.spans
        ]
        return {
            "telemetry_format": "opentelemetry-sdk",
            "pii_redaction": "enabled (Cloud DLP + Regex)",
            "total_spans": len(clean_spans),
            "trace_file": str(self.trace_file),
            "spans": clean_spans
        }

import sys
from pathlib import Path

root_dir = str(Path(__file__).resolve().parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.telemetry import TelemetryTracer

__all__ = ["TelemetryTracer"]

# Emits real-time events (Datadog etc.)
from typing import Protocol

class IEventEmitter(Protocol):
    # Emits a drift-alert event
    def emit_drift_event(self, session_id: str, drift_score: float, threshold: float) -> None:
        ...

    # Emits a latency-anomaly event
    def emit_latency_event(self, session_id: str, latency_ms: float, threshold: float) -> None:
        ...

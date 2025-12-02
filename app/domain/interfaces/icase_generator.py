# Creates Datadog Case Management objects
from typing import Protocol

class ICaseGenerator(Protocol):
    # Creates a case for drift
    def create_llm_drift_case(self, session_id: str, drift_score: float, threshold: float) -> None:
        ...

    # Creates a case for latency anomalies
    def create_latency_case(self, session_id: str, latency_ms: float, threshold: float) -> None:
        ...

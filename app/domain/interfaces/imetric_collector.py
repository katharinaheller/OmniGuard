# Sends metric values to datadog or other sinks
from typing import Protocol

class IMetricCollector(Protocol):
    # Records latency
    def record_latency_ms(self, latency: float, **ctx) -> None:
        ...

    # Records token counts
    def record_tokens(self, input_tokens: int, output_tokens: int, total_tokens: int, **ctx) -> None:
        ...

    # Records estimated cost
    def record_cost(self, cost: float, **ctx) -> None:
        ...

    # Records embedding drift scores
    def record_drift_score(self, score: float, window_size: int, **ctx) -> None:
        ...

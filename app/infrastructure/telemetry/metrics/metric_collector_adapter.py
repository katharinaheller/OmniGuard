# Adapter turning metric_collector functions into an interface implementation

from typing import Any

from app.domain.interfaces.imetric_collector import IMetricCollector

# Import the raw metric sender functions from the new telemetry location
from app.infrastructure.telemetry.metrics.metric_collector import (
    record_llm_latency_ms,
    record_llm_tokens,
    record_llm_cost_usd,
    record_embedding_drift_score,
)


class DatadogMetricCollector(IMetricCollector):
    # Records latency in ms
    def record_latency_ms(self, latency: float, **ctx) -> None:
        # # Send latency metric to Datadog
        record_llm_latency_ms(latency, None, **ctx)

    # Records token counts
    def record_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        **ctx,
    ) -> None:
        # # Send token metrics
        record_llm_tokens(input_tokens, output_tokens, total_tokens, None, **ctx)

    # Records estimated cost
    def record_cost(self, cost: float, **ctx) -> None:
        # # Send cost metric
        record_llm_cost_usd(cost, None, **ctx)

    # Records embedding drift
    def record_drift_score(self, score: float, window_size: int, **ctx) -> None:
        # # Send drift metric
        record_embedding_drift_score(score, None, window_size=window_size, **ctx)

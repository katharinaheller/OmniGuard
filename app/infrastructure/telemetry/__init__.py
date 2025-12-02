# # TELEMETRY PUBLIC API
# # This file exposes all raw data collectors (metrics, logs, spans)
# # for import by the orchestrator and other layers.

# --- Tracing ---
from .tracing.span_collector import (
    SpanSnapshot,
    capture_current_span,
    span_snapshot_to_dict,
)

# --- Metrics ---
from .metrics.metric_collector import (
    record_llm_latency_ms,
    record_llm_tokens,
    record_llm_cost_usd,
    record_embedding_drift_score,
)

# --- Logging ---
from .logging.log_collector import (
    log_event,
    configure_observability_logger,
)

__all__ = [
    # tracing
    "SpanSnapshot",
    "capture_current_span",
    "span_snapshot_to_dict",

    # metrics
    "record_llm_latency_ms",
    "record_llm_tokens",
    "record_llm_cost_usd",
    "record_embedding_drift_score",

    # logging
    "log_event",
    "configure_observability_logger",
]

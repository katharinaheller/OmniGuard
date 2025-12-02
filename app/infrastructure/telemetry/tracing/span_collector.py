from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

from ddtrace import tracer


@dataclass
class SpanSnapshot:
    # # Snapshot of the current Datadog span for later fusion with metrics and logs
    trace_id: int
    span_id: int
    name: str
    service: Optional[str]
    resource: Optional[str]
    span_type: Optional[str]
    start_ns: int
    duration_ns: Optional[int]
    meta: Dict[str, Any]
    metrics: Dict[str, float]


def _safe_int(value: Any) -> Optional[int]:
    # # Convert a value to int if possible, otherwise return None
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def capture_current_span() -> Optional[SpanSnapshot]:
    # # Capture a snapshot of the current Datadog span for correlation in dashboards
    span = tracer.current_span()
    if span is None:
        return None

    trace_id = _safe_int(getattr(span, "trace_id", None))
    span_id = _safe_int(getattr(span, "span_id", None))
    name = getattr(span, "name", "") or ""
    service = getattr(span, "service", None)
    resource = getattr(span, "resource", None)
    span_type = getattr(span, "span_type", None)

    start_ns = _safe_int(getattr(span, "start_ns", None)) or 0
    duration_ns = _safe_int(getattr(span, "duration_ns", None))

    meta = dict(getattr(span, "meta", {}) or {})
    metrics = dict(getattr(span, "metrics", {}) or {})

    return SpanSnapshot(
        trace_id=trace_id or 0,
        span_id=span_id or 0,
        name=name,
        service=service,
        resource=resource,
        span_type=span_type,
        start_ns=start_ns,
        duration_ns=duration_ns,
        meta=meta,
        metrics=metrics,
    )


def span_snapshot_to_dict(snapshot: Optional[SpanSnapshot]) -> Dict[str, Any]:
    # # Convert a SpanSnapshot to a plain dictionary for logging or metric tags
    if snapshot is None:
        return {}
    return asdict(snapshot)

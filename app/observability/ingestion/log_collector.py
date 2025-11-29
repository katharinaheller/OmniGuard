from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from ddtrace import tracer


_OBSERVABILITY_LOGGER_NAME = "omniguard.observability"


def configure_observability_logger(level: int = logging.INFO) -> logging.Logger:
    # # Configure a JSON logger for observability events if not already configured
    logger = logging.getLogger(_OBSERVABILITY_LOGGER_NAME)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    handler.setLevel(level)

    class JsonFormatter(logging.Formatter):
        # # Formatter that emits JSON lines for Datadog log ingestion
        def format(self, record: logging.LogRecord) -> str:
            payload: Dict[str, Any] = {
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if hasattr(record, "observability"):
                try:
                    payload.update(record.observability)  # type: ignore[arg-type]
                except Exception:
                    pass
            return json.dumps(payload, ensure_ascii=False)

    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def _current_trace_context() -> Dict[str, Any]:
    # # Extract current trace and span identifiers for log correlation
    span = tracer.current_span()
    if span is None:
        return {}
    context: Dict[str, Any] = {}
    trace_id = getattr(span, "trace_id", None)
    span_id = getattr(span, "span_id", None)
    if trace_id is not None:
        context["dd.trace_id"] = int(trace_id)
    if span_id is not None:
        context["dd.span_id"] = int(span_id)
    return context


def log_event(
    event_type: str,
    message: str,
    level: int = logging.INFO,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> None:
    # # Emit a structured observability event log with Datadog trace correlation
    logger = logging.getLogger(_OBSERVABILITY_LOGGER_NAME)
    if not logger.handlers:
        logger = configure_observability_logger()

    payload: Dict[str, Any] = {
        "event_type": event_type,
    }
    payload.update(_current_trace_context())
    if extra_fields:
        payload.update(extra_fields)

    record_extra = {"observability": payload}
    logger.log(level, message, extra=record_extra)

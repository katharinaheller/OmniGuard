from __future__ import annotations
from typing import Any, Iterable, List, Optional

from app.observability.export import MetricSender

_METRICS = MetricSender()


def _sanitize_tag_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip()
    if not v:
        return None
    return v.replace(" ", "_").lower()


def _build_tags(base: Optional[Iterable[str]] = None, **ctx: Any) -> List[str]:
    tags: List[str] = []
    if base:
        tags.extend(list(base))
    for key, value in ctx.items():
        val = _sanitize_tag_value(value)
        if val:
            tags.append(f"{key}:{val}")
    return tags


def record_llm_latency_ms(latency_ms: float, tags=None, **ctx):
    t = _build_tags(tags, **ctx)
    _METRICS.gauge("omniguard.llm.latency_ms", latency_ms, t)


def record_llm_tokens(input_tokens: int, output_tokens: int, total_tokens: int, tags=None, **ctx):
    t = _build_tags(tags, **ctx)
    _METRICS.gauge("omniguard.llm.tokens.input", input_tokens, t)
    _METRICS.gauge("omniguard.llm.tokens.output", output_tokens, t)
    _METRICS.gauge("omniguard.llm.tokens.total", total_tokens, t)


def record_llm_cost_usd(cost: float, tags=None, **ctx):
    t = _build_tags(tags, **ctx)
    _METRICS.gauge("omniguard.llm.cost_usd", cost, t)


def record_embedding_drift_score(score: float, tags=None, **ctx):
    t = _build_tags(tags, **ctx)
    _METRICS.gauge("omniguard.llm.embedding_drift.score", score, t)

# Fully SOLID, interface-driven LLM Orchestrator
from typing import Dict, Any, Generator
import uuid

from app.api.schemas.llm import ChatRequest, ChatResponse

# Interfaces
from app.domain.interfaces.illm_client import ILLMClient
from app.domain.interfaces.iredaction_filter import IRedactionFilter
from app.domain.interfaces.isession_tracker import ISessionTracker
from app.domain.interfaces.idrift_detector import IEmbeddingDriftDetector
from app.domain.interfaces.ievent_emitter import IEventEmitter
from app.domain.interfaces.icase_generator import ICaseGenerator
from app.domain.interfaces.imetric_collector import IMetricCollector

# Observability span helpers
from ddtrace.llmobs import LLMObs
from app.infrastructure.telemetry import (
    capture_current_span,
    span_snapshot_to_dict,
    log_event,
)


class LLMOrchestrator:
    # Orchestrator depends purely on interfaces
    def __init__(
        self,
        llm_client: ILLMClient,
        redaction: IRedactionFilter,
        session_tracker: ISessionTracker,
        drift_detector: IEmbeddingDriftDetector,
        event_emitter: IEventEmitter,
        case_generator: ICaseGenerator,
        metric_collector: IMetricCollector,
        settings: Any,
        drift_threshold: float = 0.2,
        latency_threshold_ms: float = 2000.0,
    ) -> None:
        self._client = llm_client
        self._redaction = redaction
        self._tracker = session_tracker
        self._drift = drift_detector
        self._events = event_emitter
        self._cases = case_generator
        self._metrics = metric_collector
        self._settings = settings
        self._drift_threshold = drift_threshold
        self._latency_threshold_ms = latency_threshold_ms

    def _ensure_session_id(self, req: ChatRequest) -> str:
        if req.metadata is None:
            req.metadata = {}
        sid = req.metadata.get("session_id")
        if not sid or not isinstance(sid, str):
            sid = str(uuid.uuid4())
            req.metadata["session_id"] = sid
        return sid

    def _handle_observability(
        self,
        req: ChatRequest,
        res: ChatResponse,
    ) -> None:
        session_id = self._ensure_session_id(req)

        ctx = {
            "session": session_id,
            "env": self._settings.environment,
            "service": self._settings.app_name,
            "model": self._settings.vertex_model_name,
        }

        state = self._tracker.record_turn(
            session_id=session_id,
            input_tokens=res.usage.input_tokens,
            output_tokens=res.usage.output_tokens,
            metadata=dict(ctx),
        )

        snapshot = capture_current_span()
        span_dict = span_snapshot_to_dict(snapshot)

        # Metrics
        self._metrics.record_latency_ms(res.latency_ms, **ctx)
        self._metrics.record_tokens(
            res.usage.input_tokens,
            res.usage.output_tokens,
            res.usage.total_tokens,
            **ctx,
        )
        self._metrics.record_cost(res.usage.estimated_cost_usd, **ctx)

        # Drift detection
        output_text = res.output_text or ""
        vertex_vec, minilm_vec = self._client.get_hybrid_embeddings_for_text(output_text)
        drift = self._drift.update_and_score(vertex_vec, minilm_vec)

        self._metrics.record_drift_score(
            drift.hybrid_drift_score,
            drift.window_size,
            **ctx,
        )

        log_event(
            event_type="llm_observability_summary",
            message="Observability aggregation completed",
            extra_fields={
                "session_id": session_id,
                "latency_ms": res.latency_ms,
                "total_tokens": res.usage.total_tokens,
                "drift_score": drift.hybrid_drift_score,
                "state": state.to_observability_payload(),
                "span": span_dict,
            },
        )

        # Emit events
        if drift.is_drift:
            self._events.emit_drift_event(session_id, drift.hybrid_drift_score, self._drift_threshold)
            # self._cases.create_llm_drift_case(session_id, drift.hybrid_drift_score, self._drift_threshold)

        if res.latency_ms >= self._latency_threshold_ms:
            self._events.emit_latency_event(session_id, res.latency_ms, self._latency_threshold_ms)
            # self._cases.create_latency_case(session_id, res.latency_ms, self._latency_threshold_ms)

        LLMObs.annotate(
            metadata={
                "session_id": session_id,
                "latency_ms": res.latency_ms,
                "total_tokens": res.usage.total_tokens,
                "drift_score": drift.hybrid_drift_score,
            }
        )

    def handle_chat(self, req: ChatRequest) -> ChatResponse:
        redacted = self._redaction.redact_payload(req.model_dump())
        self._ensure_session_id(req)

        with LLMObs.llm(model_name=self._settings.vertex_model_name):
            LLMObs.annotate(input_data=redacted)
            res = self._client.generate_chat(req)
            self._handle_observability(req, res)

        return res

    def handle_chat_stream(
        self,
        req: ChatRequest,
    ) -> Generator[Dict[str, Any], None, None]:
        redacted = self._redaction.redact_payload(req.model_dump())
        self._ensure_session_id(req)

        with LLMObs.llm(model_name=self._settings.vertex_model_name):
            LLMObs.annotate(input_data=redacted)
            for event in self._client.generate_chat_stream(req):
                yield event

from typing import Dict, Any, Generator
import uuid

from app.api.schemas.llm import ChatRequest, ChatResponse
from app.infrastructure.llm.vertex.client import VertexLLMClient
from app.infrastructure.config.settings import get_settings

# Datadog LLM Observability
from ddtrace.llmobs import LLMObs

# Observability ingestion (all tags sanitized centrally!)
from app.observability.ingestion import (
    record_llm_latency_ms,
    record_llm_tokens,
    record_llm_cost_usd,
    record_embedding_drift_score,
    log_event,
    capture_current_span,
    span_snapshot_to_dict,
)

from app.observability.analysis import HybridEmbeddingDriftDetector
from app.observability.enrichment import SessionTracker, RedactionFilter, RedactionConfig
from app.observability.export import DatadogEventEmitter, CaseGenerator


# --------------------------------------------------------------------
# Global singletons
# --------------------------------------------------------------------

_SESSION_TRACKER = SessionTracker()
_REDACTION_FILTER = RedactionFilter(RedactionConfig())

_DRIFT_THRESHOLD = 0.2
_DRIFT_DETECTOR = HybridEmbeddingDriftDetector(
    window_size=50,
    drift_threshold=_DRIFT_THRESHOLD,
)

try:
    _EVENT_EMITTER = DatadogEventEmitter()
except Exception:
    _EVENT_EMITTER = None

try:
    _CASE_GENERATOR = CaseGenerator()
except Exception:
    _CASE_GENERATOR = None

_LATENCY_THRESHOLD_MS = 2000.0


# --------------------------------------------------------------------
# LLM ORCHESTRATOR
# --------------------------------------------------------------------

class LLMOrchestrator:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = VertexLLMClient()

    # --------------------------
    # METADATA
    # --------------------------

    def _ensure_session_id(self, req: ChatRequest) -> str:
        if req.metadata is None:
            req.metadata = {}
        sid = req.metadata.get("session_id")
        if not sid or not isinstance(sid, str):
            sid = str(uuid.uuid4())
            req.metadata["session_id"] = sid
        return sid

    # --------------------------
    # MAIN OBS PROCESSING
    # --------------------------

    def _post_observability_processing(
        self,
        req: ChatRequest,
        res: ChatResponse,
    ) -> None:

        session_id = self._ensure_session_id(req)

        # Instead of pre-assembling tags, we pass *context values*
        # Sanitizer in metric_collector builds safe normalized tags
        tag_context = {
            "session": session_id,
            "env": self._settings.environment,
            "service": self._settings.app_name,       # sanitized → omniguard_llm_service
            "model": self._settings.vertex_model_name,
        }

        # Track session accumulation
        session_state = _SESSION_TRACKER.record_turn(
            session_id=session_id,
            input_tokens=res.usage.input_tokens,
            output_tokens=res.usage.output_tokens,
            metadata={
                "model": self._settings.vertex_model_name,
                "environment": self._settings.environment,
                "app_name": self._settings.app_name,
            },
        )

        # Capture Datadog span
        span_snapshot = capture_current_span()
        span_dict = span_snapshot_to_dict(span_snapshot)

        # ------------------
        # METRICS
        # ------------------

        record_llm_latency_ms(
            res.latency_ms,
            tags=None,
            **tag_context,
        )

        record_llm_tokens(
            input_tokens=res.usage.input_tokens,
            output_tokens=res.usage.output_tokens,
            total_tokens=res.usage.total_tokens,
            tags=None,
            **tag_context,
        )

        record_llm_cost_usd(
            cost=res.usage.estimated_cost_usd,
            tags=None,
            **tag_context,
        )

        # ------------------
        # DRIFT
        # ------------------

        output_text = res.output_text or ""
        vertex_emb, minilm_emb = self._client.get_hybrid_embeddings_for_text(output_text)

        drift_result = _DRIFT_DETECTOR.update_and_score(vertex_emb, minilm_emb)

        record_embedding_drift_score(
            score=drift_result.hybrid_drift_score,
            tags=None,
            window_size=drift_result.window_size,
            **tag_context,
        )

        # ------------------
        # LOGGING
        # ------------------

        log_event(
            event_type="llm_observability_summary",
            message="LLM request observability summary",
            extra_fields={
                "session_id": session_id,
                "latency_ms": res.latency_ms,
                "input_tokens": res.usage.input_tokens,
                "output_tokens": res.usage.output_tokens,
                "total_tokens": res.usage.total_tokens,
                "hybrid_drift_score": drift_result.hybrid_drift_score,
                "vertex_drift_score": drift_result.vertex_drift_score,
                "minilm_drift_score": drift_result.minilm_drift_score,
                "embedding_drift_window_size": drift_result.window_size,
                "embedding_drift_flag": drift_result.is_drift,
                "session_state": session_state.to_observability_payload(),
                "span": span_dict,
            },
        )

        # ------------------
        # CASES / EVENTS
        # ------------------

        if drift_result.is_drift:
            if _EVENT_EMITTER:
                _EVENT_EMITTER.emit_drift_event(
                    session_id, drift_result.hybrid_drift_score, _DRIFT_THRESHOLD
                )
            if _CASE_GENERATOR:
                _CASE_GENERATOR.create_llm_drift_case(
                    session_id, drift_result.hybrid_drift_score, _DRIFT_THRESHOLD
                )

        if res.latency_ms >= _LATENCY_THRESHOLD_MS:
            if _EVENT_EMITTER:
                _EVENT_EMITTER.emit_latency_event(
                    session_id, res.latency_ms, _LATENCY_THRESHOLD_MS
                )
            if _CASE_GENERATOR:
                _CASE_GENERATOR.create_latency_case(
                    session_id, res.latency_ms, _LATENCY_THRESHOLD_MS
                )

        # ------------------
        # ANNOTATE LLMOBS
        # ------------------

        LLMObs.annotate(
            metadata={
                "session_id": session_id,
                "latency_ms": res.latency_ms,
                "input_tokens": res.usage.input_tokens,
                "output_tokens": res.usage.output_tokens,
                "total_tokens": res.usage.total_tokens,
                "estimated_cost_usd": res.usage.estimated_cost_usd,
                "hybrid_drift_score": drift_result.hybrid_drift_score,
                "vertex_drift_score": drift_result.vertex_drift_score,
                "minilm_drift_score": drift_result.minilm_drift_score,
                "embedding_drift_window_size": drift_result.window_size,
                "embedding_drift_flag": drift_result.is_drift,
            }
        )

    # --------------------------
    # NON-STREAMING
    # --------------------------

    def handle_chat(self, req: ChatRequest) -> ChatResponse:
        self._enrich_request_metadata(req)
        self._ensure_session_id(req)

        redacted = _REDACTION_FILTER.redact_payload(req.model_dump())

        with LLMObs.llm(model_name=self._settings.vertex_model_name):
            LLMObs.annotate(input_data=redacted)
            response = self._client.generate_chat(req)
            self._post_observability_processing(req, response)

        return response

    # --------------------------
    # STREAMING
    # --------------------------

    def handle_chat_stream(
        self,
        req: ChatRequest,
    ) -> Generator[Dict[str, Any], None, None]:

        self._enrich_request_metadata(req)
        self._ensure_session_id(req)

        with LLMObs.llm(model_name=self._settings.vertex_model_name):
            LLMObs.annotate(input_data=_REDACTION_FILTER.redact_payload(req.model_dump()))

            for event in self._client.generate_chat_stream(req):
                yield event

    def _enrich_request_metadata(self, req: ChatRequest) -> None:
        if req.metadata is None:
            req.metadata = {}
        req.metadata.setdefault("app_name", self._settings.app_name)
        req.metadata.setdefault("environment", self._settings.environment)

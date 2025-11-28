from typing import Dict, Any, Generator

from app.api.schemas.llm import ChatRequest, ChatResponse
from app.infrastructure.llm.vertex.client import VertexLLMClient
from app.infrastructure.config.settings import get_settings


class LLMOrchestrator:
    # # Encapsulates application-level logic around the LLM calls
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = VertexLLMClient()

    def handle_chat(self, req: ChatRequest) -> ChatResponse:
        # # Entry point for non-streaming chat
        self._enrich_request_metadata(req)
        response = self._client.generate_chat(req)
        self._emit_observability_signals(req, response)
        return response

    def handle_chat_stream(
        self, req: ChatRequest
    ) -> Generator[Dict[str, Any], None, None]:
        # # Entry point for streaming chat
        self._enrich_request_metadata(req)
        for event in self._client.generate_chat_stream(req):
            # # You can attach incremental observability here if needed
            yield event

    def _enrich_request_metadata(self, req: ChatRequest) -> None:
        # # Add orchestrator-level metadata such as app/environment
        if req.metadata is None:
            req.metadata = {}
        req.metadata.setdefault("app_name", self._settings.app_name)
        req.metadata.setdefault("environment", self._settings.environment)

    def _emit_observability_signals(
        self,
        req: ChatRequest,
        res: ChatResponse,
    ) -> None:
        # # Placeholder for Datadog logging/metrics/tracing integration
        # # Example:
        # # - log latency_ms, tokens, model, environment
        # # - emit custom metrics via Datadog client
        # # - enrich APM traces with LLM metadata
        if not self._settings.telemetry_enabled:
            return

        # # Here you would call out to your telemetry layer
        # # Example pseudo-invocations:
        # # datadog_metrics.record_llm_latency(res.latency_ms, model=res.model, env=self._settings.environment)
        # # datadog_metrics.record_llm_tokens(res.usage.total_tokens, model=res.model, env=self._settings.environment)
        # # datadog_logger.info("llm_request", extra={...})
        return

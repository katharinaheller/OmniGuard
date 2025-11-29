from typing import Dict, Any, Generator

from app.api.schemas.llm import ChatRequest, ChatResponse
from app.infrastructure.llm.vertex.client import VertexLLMClient
from app.infrastructure.config.settings import get_settings

# # Datadog LLMObs
from ddtrace.llmobs import LLMObs

class LLMOrchestrator:
    # # Encapsulates application-level logic around the LLM calls
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = VertexLLMClient()

    def handle_chat(self, req: ChatRequest) -> ChatResponse:
        # # Enrich metadata
        self._enrich_request_metadata(req)

        # # Datadog LLM Span
        with LLMObs.llm(model_name=self._settings.vertex_model_name):
            LLMObs.annotate(input_data=req.model_dump())

            response = self._client.generate_chat(req)

            # # Annotate output, latency, tokens, cost
            LLMObs.annotate(
                output_data=response.output_text,
                metadata={
                    "latency_ms": response.latency_ms,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "estimated_cost_usd": response.usage.estimated_cost_usd,
                },
            )

        return response

    def handle_chat_stream(
        self, req: ChatRequest
    ) -> Generator[Dict[str, Any], None, None]:
        # # Metadata enrichment
        self._enrich_request_metadata(req)

        # # Streaming LLM Span
        with LLMObs.llm(model_name=self._settings.vertex_model_name):
            LLMObs.annotate(input_data=req.model_dump())

            for event in self._client.generate_chat_stream(req):
                yield event

            # # Final event is emitted inside client

    def _enrich_request_metadata(self, req: ChatRequest) -> None:
        if req.metadata is None:
            req.metadata = {}
        req.metadata.setdefault("app_name", self._settings.app_name)
        req.metadata.setdefault("environment", self._settings.environment)

    def _emit_observability_signals(
        self,
        req: ChatRequest,
        res: ChatResponse,
    ) -> None:
        # # No-op — replaced by Datadog LLMObs
        return

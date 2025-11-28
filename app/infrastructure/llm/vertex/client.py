import time
import uuid
from typing import Generator, Iterable, Dict, Any

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Content, Part

from app.infrastructure.config.settings import get_settings
from app.api.schemas.llm import ChatRequest, ChatResponse, UsageInfo


class VertexLLMClient:
    # # Thin wrapper around Vertex AI GenerativeModel for Gemini
    def __init__(self) -> None:
        self._settings = get_settings()
        self._initialized = False
        self._model: GenerativeModel | None = None

    def _init_client(self) -> None:
        # # Lazy initialization of the Vertex AI client and model
        if self._initialized:
            return

        vertexai.init(
            project=self._settings.gcp_project_id,
            location=self._settings.gcp_location,
        )
        self._model = GenerativeModel(self._settings.vertex_model_name)
        self._initialized = True

    def _build_generation_config(self, req: ChatRequest) -> GenerationConfig:
        # # Map request level parameters to Vertex generation config
        return GenerationConfig(
            max_output_tokens=req.max_output_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
        )

    def _convert_messages_to_vertex_content(self, req: ChatRequest) -> Iterable[Content]:
        # # Transform generic ChatRequest messages into Vertex Content objects
        contents: list[Content] = []
        for msg in req.messages:
            part = Part.from_text(msg.content)
            contents.append(
                Content(
                    role=msg.role,
                    parts=[part],
                )
            )
        return contents

    def generate_chat(self, req: ChatRequest) -> ChatResponse:
        # # Non-streaming call that returns a fully assembled ChatResponse
        self._init_client()
        assert self._model is not None

        generation_config = self._build_generation_config(req)
        contents = list(self._convert_messages_to_vertex_content(req))

        start = time.perf_counter()
        response = self._model.generate_content(
            contents=contents,
            generation_config=generation_config,
            safety_settings=None,
            stream=False,
        )
        end = time.perf_counter()

        latency_ms = (end - start) * 1000.0
        usage = self._extract_usage(response)

        output_text = response.text if hasattr(response, "text") else ""

        chat_response = ChatResponse(
            id=str(uuid.uuid4()),
            model=self._settings.vertex_model_name,
            created_at=self._now_utc(),
            latency_ms=latency_ms,
            usage=usage,
            output_text=output_text,
            raw_model_metadata=self._extract_raw_metadata(response),
        )

        return chat_response

    def generate_chat_stream(
        self, req: ChatRequest
    ) -> Generator[Dict[str, Any], None, None]:
        # # Streaming call that yields partial chunks suitable for SSE or chunked HTTP
        self._init_client()
        assert self._model is not None

        generation_config = self._build_generation_config(req)
        contents = list(self._convert_messages_to_vertex_content(req))

        start = time.perf_counter()
        stream = self._model.generate_content(
            contents=contents,
            generation_config=generation_config,
            safety_settings=None,
            stream=True,
        )

        total_text_parts: list[str] = []
        final_usage = UsageInfo()

        for chunk in stream:
            # # Extract incremental text for this chunk
            text_fragment = getattr(chunk, "text", "") or ""
            if text_fragment:
                total_text_parts.append(text_fragment)

                yield {
                    "type": "chunk",
                    "text": text_fragment,
                }

            # # Update usage from chunk if available
            usage = self._extract_usage(chunk)
            if usage.total_tokens > 0:
                final_usage = usage

        end = time.perf_counter()
        latency_ms = (end - start) * 1000.0

        full_text = "".join(total_text_parts)

        yield {
            "type": "final",
            "id": str(uuid.uuid4()),
            "model": self._settings.vertex_model_name,
            "latency_ms": latency_ms,
            "usage": final_usage.model_dump(),
            "output_text": full_text,
        }

    def _extract_usage(self, response: Any) -> UsageInfo:
        # # Extract token usage if available on the response
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return UsageInfo()

        input_tokens = getattr(usage, "input_token_count", 0) or 0
        output_tokens = getattr(usage, "output_token_count", 0) or 0
        total_tokens = getattr(usage, "total_token_count", 0) or (
            input_tokens + output_tokens
        )

        # # Placeholder: you can compute a real cost based on pricing tables here
        estimated_cost_usd = 0.0

        return UsageInfo(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )

    def _extract_raw_metadata(self, response: Any) -> Dict[str, Any]:
        # # Extract raw metadata for observability and debugging
        metadata: Dict[str, Any] = {}
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            metadata["usage_metadata"] = {
                "input_token_count": getattr(usage, "input_token_count", None),
                "output_token_count": getattr(usage, "output_token_count", None),
                "total_token_count": getattr(usage, "total_token_count", None),
            }

        # # You can add safety ratings or citations if the model returns them
        safety_ratings = getattr(response, "safety_ratings", None)
        if safety_ratings is not None:
            metadata["safety_ratings"] = [str(r) for r in safety_ratings]

        return metadata

    @staticmethod
    def _now_utc():
        # # Use datetime in a local helper to avoid global import cycles
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)

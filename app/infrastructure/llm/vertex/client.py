import time
import uuid
from typing import Generator, Iterable, Dict, Any, List

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Content, Part
from vertexai.language_models import TextEmbeddingModel

from app.infrastructure.config.settings import get_settings
from app.api.schemas.llm import ChatRequest, ChatResponse, UsageInfo

# Datadog LLMObs
from ddtrace.llmobs import LLMObs

# Optional MiniLM embeddings via sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None  # type: ignore[assignment]


class VertexLLMClient:
    # # Thin wrapper around Vertex AI GenerativeModel and TextEmbeddingModel for Gemini
    def __init__(self) -> None:
        self._settings = get_settings()
        self._initialized = False
        self._model: GenerativeModel | None = None

        self._embedding_model: TextEmbeddingModel | None = None
        self._minilm_model: Any | None = None

    def _init_client(self) -> None:
        # # Lazily initialize Vertex AI generative client
        if self._initialized:
            return

        vertexai.init(
            project=self._settings.gcp_project_id,
            location=self._settings.gcp_location,
        )
        self._model = GenerativeModel(self._settings.vertex_model_name)
        self._initialized = True

    def _init_embedding_clients(self) -> None:
        # # Lazily initialize Vertex text embeddings and MiniLM sentence encoder
        if self._embedding_model is None:
            try:
                self._embedding_model = TextEmbeddingModel.from_pretrained(
                    "textembedding-gecko@latest"
                )
            except Exception:
                self._embedding_model = None

        if self._minilm_model is None and SentenceTransformer is not None:
            try:
                self._minilm_model = SentenceTransformer(
                    "sentence-transformers/all-MiniLM-L6-v2"
                )
            except Exception:
                self._minilm_model = None

    def _build_generation_config(self, req: ChatRequest) -> GenerationConfig:
        # # Map ChatRequest sampling parameters to Vertex generation config
        return GenerationConfig(
            max_output_tokens=req.max_output_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
        )

    def _convert_messages_to_vertex_content(self, req: ChatRequest) -> Iterable[Content]:
        # # Convert OmniGuard chat messages to Vertex AI Content objects
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

    def get_hybrid_embeddings_for_text(
        self,
        text: str,
    ) -> tuple[List[float], List[float]]:
        # # Compute Vertex and MiniLM embeddings for the same text
        self._init_embedding_clients()

        vertex_vec: List[float] = []
        minilm_vec: List[float] = []

        if self._embedding_model is not None and text:
            try:
                embeddings = self._embedding_model.get_embeddings([text])
                if embeddings:
                    emb = embeddings[0]
                    if hasattr(emb, "values"):
                        values = getattr(emb, "values") or []
                        vertex_vec = [float(x) for x in values]
                    elif isinstance(emb, dict) and "values" in emb:
                        values = emb["values"] or []
                        vertex_vec = [float(x) for x in values]
                    elif isinstance(emb, (list, tuple)):
                        vertex_vec = [float(x) for x in emb]
            except Exception:
                vertex_vec = []

        if self._minilm_model is not None and text:
            try:
                encoded = self._minilm_model.encode(text)
                if hasattr(encoded, "tolist"):
                    minilm_vec = [float(x) for x in encoded.tolist()]
                else:
                    minilm_vec = [float(x) for x in encoded]
            except Exception:
                minilm_vec = []

        return vertex_vec, minilm_vec

    def generate_chat(self, req: ChatRequest) -> ChatResponse:
        # # Execute a non-streaming chat completion via Gemini on Vertex AI
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

        # # Emit core metrics into the LLMObs span
        LLMObs.annotate(
            metadata={
                "latency_ms": latency_ms,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
            }
        )

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
        self,
        req: ChatRequest,
    ) -> Generator[Dict[str, Any], None, None]:
        # # Execute a streaming chat completion and yield JSON compatible fragments
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
            text_fragment = getattr(chunk, "text", "") or ""
            if text_fragment:
                total_text_parts.append(text_fragment)
                yield {"type": "chunk", "text": text_fragment}

            usage = self._extract_usage(chunk)
            if usage.total_tokens > 0:
                final_usage = usage

        end = time.perf_counter()
        latency_ms = (end - start) * 1000.0
        full_text = "".join(total_text_parts)

        # # Annotate final streaming output in LLMObs span
        LLMObs.annotate(
            output_data=full_text,
            metadata={
                "latency_ms": latency_ms,
                "input_tokens": final_usage.input_tokens,
                "output_tokens": final_usage.output_tokens,
                "total_tokens": final_usage.total_tokens,
            },
        )

        yield {
            "type": "final",
            "id": str(uuid.uuid4()),
            "model": self._settings.vertex_model_name,
            "latency_ms": latency_ms,
            "usage": final_usage.model_dump(),
            "output_text": full_text,
        }

    def _extract_usage(self, response: Any) -> UsageInfo:
        # # Extract token usage from Vertex response object
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return UsageInfo()

        input_tokens = getattr(usage, "input_token_count", 0) or 0
        output_tokens = getattr(usage, "output_token_count", 0) or 0
        total_tokens = getattr(usage, "total_token_count", 0) or (
            input_tokens + output_tokens
        )

        return UsageInfo(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=0.0,
        )

    def _extract_raw_metadata(self, response: Any) -> Dict[str, Any]:
        # # Extract raw metadata snapshot from Vertex response for diagnostics
        metadata: Dict[str, Any] = {}
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            metadata["usage_metadata"] = {
                "input_token_count": getattr(usage, "input_token_count", None),
                "output_token_count": getattr(usage, "output_token_count", None),
                "total_token_count": getattr(usage, "total_token_count", None),
            }
        safety_ratings = getattr(response, "safety_ratings", None)
        if safety_ratings is not None:
            metadata["safety_ratings"] = [str(r) for r in safety_ratings]
        return metadata

    @staticmethod
    def _now_utc():
        # # Return current UTC time with timezone information
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)

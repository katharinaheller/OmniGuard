from typing import Any, Dict, Generator
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.schemas.llm import ChatRequest, ChatResponse
from app.application.orchestrators.llm_orchestrator import LLMOrchestrator

# Datadog LLMObs decorators
from ddtrace.llmobs.decorators import workflow

# Observability log helper
from app.observability.ingestion import log_event

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def get_llm_orchestrator() -> LLMOrchestrator:
    # # Dependency injection factory for orchestrator
    return LLMOrchestrator()


def _ensure_session_id(req: ChatRequest) -> str:
    # # Ensure that the request metadata contains a stable session_id
    if req.metadata is None:
        req.metadata = {}
    session_id_raw = req.metadata.get("session_id")
    if not isinstance(session_id_raw, str) or not session_id_raw:
        session_id_raw = str(uuid4())
        req.metadata["session_id"] = session_id_raw
    return session_id_raw


@router.post("", response_model=ChatResponse)
@workflow()  # # Create workflow root span for Datadog LLMObs
async def chat_endpoint(
    req: ChatRequest,
    orchestrator: LLMOrchestrator = Depends(get_llm_orchestrator),
) -> ChatResponse:
    # # Attach or create session_id for observability and correlation
    session_id = _ensure_session_id(req)

    # # High level request log correlated with current span
    log_event(
        event_type="chat_request",
        message="Received non-streaming chat request",
        extra_fields={"session_id": session_id},
    )

    from ddtrace.llmobs import LLMObs
    LLMObs.annotate(input_data=req.model_dump())

    response = orchestrator.handle_chat(req)

    # # High level response log with latency and usage
    log_event(
        event_type="chat_response",
        message="Completed non-streaming chat request",
        extra_fields={
            "session_id": session_id,
            "latency_ms": response.latency_ms,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
        },
    )

    LLMObs.annotate(output_data=response.model_dump())

    return response


@router.post("/stream")
@workflow()  # # Workflow span also for streaming endpoint
async def chat_stream_endpoint(
    req: ChatRequest,
    orchestrator: LLMOrchestrator = Depends(get_llm_orchestrator),
) -> StreamingResponse:
    # # Attach or create session_id for streaming observability
    session_id = _ensure_session_id(req)

    from ddtrace.llmobs import LLMObs
    LLMObs.annotate(input_data=req.model_dump())

    # # Log that streaming response is starting
    log_event(
        event_type="chat_stream_request",
        message="Received streaming chat request",
        extra_fields={"session_id": session_id},
    )

    def event_generator() -> Generator[bytes, None, None]:
        # # Stream JSON lines and allow orchestrator and client to add telemetry
        for event in orchestrator.handle_chat_stream(req):
            import json
            payload = json.dumps(event, ensure_ascii=False)
            yield (payload + "\n").encode("utf-8")

    return StreamingResponse(event_generator(), media_type="application/json")

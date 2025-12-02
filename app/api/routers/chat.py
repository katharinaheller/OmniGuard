# Chat Router with fully SOLID dependency-injected orchestrator
from typing import Any, Dict, Generator
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.schemas.llm import ChatRequest, ChatResponse
from app.application.orchestrators.llm_orchestrator import LLMOrchestrator

# Dependency Injection factory
from app.infrastructure.factories.orchestrator_factory import build_llm_orchestrator

# Datadog LLMObs workflow decorator
from ddtrace.llmobs.decorators import workflow

# Correct telemetry event logger
from app.infrastructure.telemetry.logging.log_collector import log_event


router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def get_llm_orchestrator() -> LLMOrchestrator:
    # Dependency-injected orchestrator with full SOLID wiring
    return build_llm_orchestrator()


def _ensure_session_id(req: ChatRequest) -> str:
    # Ensures each request has a persistent session_id
    if req.metadata is None:
        req.metadata = {}
    session_id_raw = req.metadata.get("session_id")
    if not isinstance(session_id_raw, str) or not session_id_raw:
        session_id_raw = str(uuid4())
        req.metadata["session_id"] = session_id_raw
    return session_id_raw


@router.post("", response_model=ChatResponse)
@workflow()  # Datadog workflow root span
async def chat_endpoint(
    req: ChatRequest,
    orchestrator: LLMOrchestrator = Depends(get_llm_orchestrator),
) -> ChatResponse:
    session_id = _ensure_session_id(req)

    log_event(
        event_type="chat_request",
        message="Received non-streaming chat request",
        extra_fields={"session_id": session_id},
    )

    from ddtrace.llmobs import LLMObs
    LLMObs.annotate(input_data=req.model_dump())

    response = orchestrator.handle_chat(req)

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
@workflow()  # Datadog workflow span for streaming mode
async def chat_stream_endpoint(
    req: ChatRequest,
    orchestrator: LLMOrchestrator = Depends(get_llm_orchestrator),
) -> StreamingResponse:
    session_id = _ensure_session_id(req)

    from ddtrace.llmobs import LLMObs
    LLMObs.annotate(input_data=req.model_dump())

    log_event(
        event_type="chat_stream_request",
        message="Received streaming chat request",
        extra_fields={"session_id": session_id},
    )

    def event_generator() -> Generator[bytes, None, None]:
        # Streams JSON lines produced by orchestrator
        for event in orchestrator.handle_chat_stream(req):
            import json
            payload = json.dumps(event, ensure_ascii=False)
            yield (payload + "\n").encode("utf-8")

    return StreamingResponse(event_generator(), media_type="application/json")

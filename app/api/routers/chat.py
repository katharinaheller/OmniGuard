from typing import Any, Dict, Generator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.schemas.llm import ChatRequest, ChatResponse
from app.application.orchestrators.llm_orchestrator import LLMOrchestrator

# # Datadog LLMObs decorators
from ddtrace.llmobs.decorators import workflow

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def get_llm_orchestrator() -> LLMOrchestrator:
    # # Dependency injection factory for orchestrator
    return LLMOrchestrator()


@router.post("", response_model=ChatResponse)
@workflow()  # # Create workflow root span
async def chat_endpoint(
    req: ChatRequest,
    orchestrator: LLMOrchestrator = Depends(get_llm_orchestrator),
) -> ChatResponse:
    # # Annotate workflow span input
    from ddtrace.llmobs import LLMObs
    LLMObs.annotate(input_data=req.model_dump())

    response = orchestrator.handle_chat(req)

    # # Annotate workflow span output
    LLMObs.annotate(output_data=response.model_dump())

    return response


@router.post("/stream")
@workflow()  # # Workflow span also for stream
async def chat_stream_endpoint(
    req: ChatRequest,
    orchestrator: LLMOrchestrator = Depends(get_llm_orchestrator),
) -> StreamingResponse:

    from ddtrace.llmobs import LLMObs
    LLMObs.annotate(input_data=req.model_dump())

    def event_generator() -> Generator[bytes, None, None]:
        for event in orchestrator.handle_chat_stream(req):
            import json
            payload = json.dumps(event, ensure_ascii=False)
            yield (payload + "\n").encode("utf-8")

        # # No output annotation here because streaming final event carries data

    return StreamingResponse(event_generator(), media_type="application/json")

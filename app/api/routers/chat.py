from typing import Any, Dict, Generator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.schemas.llm import ChatRequest, ChatResponse
from app.application.orchestrators.llm_orchestrator import LLMOrchestrator

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def get_llm_orchestrator() -> LLMOrchestrator:
    # # Dependency injection factory for orchestrator
    return LLMOrchestrator()


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    orchestrator: LLMOrchestrator = Depends(get_llm_orchestrator),
) -> ChatResponse:
    # # Non-streaming chat endpoint
    # # FastAPI automatically runs sync code in a threadpool when needed
    return orchestrator.handle_chat(req)


@router.post("/stream")
async def chat_stream_endpoint(
    req: ChatRequest,
    orchestrator: LLMOrchestrator = Depends(get_llm_orchestrator),
) -> StreamingResponse:
    # # Streaming endpoint using chunked transfer
    def event_generator() -> Generator[bytes, None, None]:
        for event in orchestrator.handle_chat_stream(req):
            # # Encode each event as a JSON line
            import json

            payload = json.dumps(event, ensure_ascii=False)
            yield (payload + "\n").encode("utf-8")

    return StreamingResponse(
        event_generator(),
        media_type="application/json",
    )

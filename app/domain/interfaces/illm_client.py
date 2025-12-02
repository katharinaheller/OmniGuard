# Defines the contract for an LLM backend client
from typing import Protocol, Dict, Any, Generator
from app.api.schemas.llm import ChatRequest, ChatResponse

class ILLMClient(Protocol):
    # Executes a regular text generation request
    def generate_chat(self, req: ChatRequest) -> ChatResponse:
        ...

    # Executes a streaming generation request
    def generate_chat_stream(
        self,
        req: ChatRequest,
    ) -> Generator[Dict[str, Any], None, None]:
        ...

# Tracks conversational session states
from typing import Protocol, Dict, Any
from app.observability.enrichment.session_tracker import SessionState

class ISessionTracker(Protocol):
    # Records a single LLM turn
    def record_turn(
        self,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
        metadata: Dict[str, Any],
    ) -> SessionState:
        ...

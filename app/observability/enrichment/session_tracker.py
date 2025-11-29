from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


@dataclass
class SessionEvent:
    # # Single event in a session timeline
    timestamp: datetime
    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionState:
    # # Aggregate state for a session
    session_id: str
    created_at: datetime
    last_activity: datetime
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    turn_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    events: List[SessionEvent] = field(default_factory=list)

    def to_observability_payload(self) -> Dict[str, Any]:
        # # Convert state into a compact payload for Datadog annotation or metrics
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "turn_count": self.turn_count,
            "metadata": dict(self.metadata),
        }


class SessionTracker:
    # # In-memory session tracker for LLM conversations
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}

    def _now_utc(self) -> datetime:
        # # Return current UTC timestamp
        return datetime.now(timezone.utc)

    def start_session(
        self,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionState:
        # # Start or rehydrate a session with optional metadata
        now = self._now_utc()
        if metadata is None:
            metadata = {}
        state = self._sessions.get(session_id)
        if state is None:
            state = SessionState(
                session_id=session_id,
                created_at=now,
                last_activity=now,
                metadata=dict(metadata),
            )
            self._sessions[session_id] = state
        else:
            state.last_activity = now
            state.metadata.update(metadata)
        state.events.append(
            SessionEvent(
                timestamp=now,
                event_type="session_started",
                payload={"metadata": dict(metadata)},
            )
        )
        return state

    def record_turn(
        self,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionState:
        # # Record a single LLM turn for a session
        if metadata is None:
            metadata = {}
        state = self._sessions.get(session_id)
        if state is None:
            state = self.start_session(session_id=session_id, metadata=metadata)
        now = self._now_utc()
        state.total_input_tokens += max(0, int(input_tokens))
        state.total_output_tokens += max(0, int(output_tokens))
        state.turn_count += 1
        state.last_activity = now
        state.metadata.update(metadata)
        state.events.append(
            SessionEvent(
                timestamp=now,
                event_type="llm_turn",
                payload={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "metadata": dict(metadata),
                },
            )
        )
        return state

    def end_session(
        self,
        session_id: str,
        reason: str = "normal",
    ) -> Optional[SessionState]:
        # # Mark a session as ended and return its final state
        state = self._sessions.get(session_id)
        if state is None:
            return None
        now = self._now_utc()
        state.last_activity = now
        state.events.append(
            SessionEvent(
                timestamp=now,
                event_type="session_ended",
                payload={"reason": reason},
            )
        )
        return state

    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        # # Return current state of a session
        return self._sessions.get(session_id)

    def get_all_sessions(self) -> List[SessionState]:
        # # Return states of all known sessions
        return list(self._sessions.values())

    def export_for_datadog(self, session_id: str) -> Optional[Dict[str, Any]]:
        # # Export a Datadog friendly view of a session
        state = self._sessions.get(session_id)
        if state is None:
            return None
        return state.to_observability_payload()

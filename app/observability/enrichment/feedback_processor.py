from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


@dataclass
class FeedbackEvent:
    # # Single user feedback signal for a session
    timestamp: datetime
    session_id: str
    rating: float
    comment: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackAggregate:
    # # Aggregated feedback statistics for a session
    session_id: str
    count: int
    average_rating: float
    last_rating: float
    last_comment: Optional[str]
    last_timestamp: datetime

    def to_observability_payload(self) -> Dict[str, Any]:
        # # Convert aggregate into Datadog friendly structure
        return {
            "session_id": self.session_id,
            "count": self.count,
            "average_rating": self.average_rating,
            "last_rating": self.last_rating,
            "last_comment": self.last_comment,
            "last_timestamp": self.last_timestamp.isoformat(),
        }


class FeedbackProcessor:
    # # In-memory feedback processor with simple statistics
    def __init__(self) -> None:
        self._events_by_session: Dict[str, List[FeedbackEvent]] = {}

    def _now_utc(self) -> datetime:
        # # Return current UTC timestamp
        return datetime.now(timezone.utc)

    def submit_feedback(
        self,
        session_id: str,
        rating: float,
        comment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FeedbackAggregate:
        # # Record feedback for a session and update aggregates
        if metadata is None:
            metadata = {}
        events = self._events_by_session.get(session_id)
        if events is None:
            events = []
            self._events_by_session[session_id] = events
        event = FeedbackEvent(
            timestamp=self._now_utc(),
            session_id=session_id,
            rating=float(rating),
            comment=comment,
            metadata=dict(metadata),
        )
        events.append(event)
        return self._aggregate_for_session(session_id)

    def _aggregate_for_session(self, session_id: str) -> FeedbackAggregate:
        # # Compute aggregate feedback statistics for a session
        events = self._events_by_session.get(session_id, [])
        if not events:
            now = self._now_utc()
            return FeedbackAggregate(
                session_id=session_id,
                count=0,
                average_rating=0.0,
                last_rating=0.0,
                last_comment=None,
                last_timestamp=now,
            )
        count = len(events)
        rating_sum = sum(e.rating for e in events)
        average = rating_sum / float(count)
        last_event = events[-1]
        return FeedbackAggregate(
            session_id=session_id,
            count=count,
            average_rating=average,
            last_rating=last_event.rating,
            last_comment=last_event.comment,
            last_timestamp=last_event.timestamp,
        )

    def get_session_feedback(
        self,
        session_id: str,
    ) -> FeedbackAggregate:
        # # Return current aggregate feedback for a session
        return self._aggregate_for_session(session_id)

    def get_global_score(self) -> FeedbackAggregate:
        # # Compute a single global aggregate feedback summary across all sessions
        all_events: List[FeedbackEvent] = []
        for events in self._events_by_session.values():
            all_events.extend(events)
        if not all_events:
            now = self._now_utc()
            return FeedbackAggregate(
                session_id="GLOBAL",
                count=0,
                average_rating=0.0,
                last_rating=0.0,
                last_comment=None,
                last_timestamp=now,
            )
        count = len(all_events)
        rating_sum = sum(e.rating for e in all_events)
        average = rating_sum / float(count)
        last_event = all_events[-1]
        return FeedbackAggregate(
            session_id="GLOBAL",
            count=count,
            average_rating=average,
            last_rating=last_event.rating,
            last_comment=last_event.comment,
            last_timestamp=last_event.timestamp,
        )

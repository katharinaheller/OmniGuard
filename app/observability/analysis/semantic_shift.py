from __future__ import annotations

from dataclasses import dataclass
from typing import Deque, Dict, List, Optional
from collections import deque
import math


def _l2_distance(a: List[float], b: List[float]) -> float:
    # # Compute L2 distance between two vectors
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    acc = 0.0
    for xa, xb in zip(a, b):
        diff = xa - xb
        acc += diff * diff
    return math.sqrt(acc)


@dataclass
class SemanticShiftSnapshot:
    # # Snapshot of semantic shift state at a given time
    key: str
    window_size: int
    last_distance: float
    mean_distance: float
    max_distance: float


class SemanticShiftEngine:
    # # Tracks semantic shift for arbitrary keys (for example prompts, sessions or features)
    def __init__(self, window_size: int = 100) -> None:
        self._window_size = max(1, window_size)
        self._history: Dict[str, Deque[List[float]]] = {}
        self._distances: Dict[str, Deque[float]] = {}

    def _get_history(self, key: str) -> Deque[List[float]]:
        # # Return or create the embedding history for a key
        if key not in self._history:
            self._history[key] = deque(maxlen=self._window_size)
        return self._history[key]

    def _get_distance_history(self, key: str) -> Deque[float]:
        # # Return or create the distance history for a key
        if key not in self._distances:
            self._distances[key] = deque(maxlen=self._window_size)
        return self._distances[key]

    def update(
        self,
        key: str,
        embedding: List[float],
        reference_embedding: Optional[List[float]] = None,
    ) -> SemanticShiftSnapshot:
        # # Update semantic shift state for a key and return a snapshot
        history = self._get_history(key)
        dist_history = self._get_distance_history(key)

        if reference_embedding is None:
            if not history:
                last_distance = 0.0
            else:
                last_distance = _l2_distance(embedding, history[-1])
        else:
            last_distance = _l2_distance(embedding, reference_embedding)

        dist_history.append(last_distance)
        history.append(embedding)

        if dist_history:
            mean_distance = sum(dist_history) / float(len(dist_history))
            max_distance = max(dist_history)
        else:
            mean_distance = 0.0
            max_distance = 0.0

        return SemanticShiftSnapshot(
            key=key,
            window_size=len(history),
            last_distance=last_distance,
            mean_distance=mean_distance,
            max_distance=max_distance,
        )

    def get_snapshot(self, key: str) -> Optional[SemanticShiftSnapshot]:
        # # Return the latest snapshot for a key without updating
        history = self._history.get(key)
        dist_history = self._distances.get(key)
        if not history or not dist_history:
            return None
        last_distance = dist_history[-1]
        mean_distance = sum(dist_history) / float(len(dist_history))
        max_distance = max(dist_history)
        return SemanticShiftSnapshot(
            key=key,
            window_size=len(history),
            last_distance=last_distance,
            mean_distance=mean_distance,
            max_distance=max_distance,
        )

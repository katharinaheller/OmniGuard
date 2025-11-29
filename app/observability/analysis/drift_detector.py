from __future__ import annotations

from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple
from collections import deque
import math


def _cosine_distance(a: List[float], b: List[float]) -> float:
    # # Compute cosine distance (1 - cosine similarity) between two vectors
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for xa, xb in zip(a, b):
        dot += xa * xb
        na += xa * xa
        nb += xb * xb
    if na == 0.0 or nb == 0.0:
        return 0.0
    return 1.0 - dot / (math.sqrt(na) * math.sqrt(nb))


@dataclass
class DriftResult:
    # # Result of a single drift evaluation step
    window_size: int
    hybrid_drift_score: float
    vertex_drift_score: float
    minilm_drift_score: float
    is_drift: bool


class HybridEmbeddingDriftDetector:
    # # Hybrid drift detector that combines Vertex and MiniLM embeddings
    def __init__(
        self,
        window_size: int = 50,
        drift_threshold: float = 0.2,
    ) -> None:
        # # window_size defines how many recent points to use as baseline
        # # drift_threshold is applied to the hybrid score
        self._window_size = max(1, window_size)
        self._drift_threshold = max(0.0, drift_threshold)

        self._vertex_history: Deque[List[float]] = deque(maxlen=self._window_size)
        self._minilm_history: Deque[List[float]] = deque(maxlen=self._window_size)

    @property
    def window_size(self) -> int:
        # # Return the effective window size
        return self._window_size

    def _baseline_centroid(
        self,
        history: Deque[List[float]],
    ) -> Optional[List[float]]:
        # # Compute centroid of embeddings in the given history
        if not history:
            return None
        dim = len(history[0])
        if dim == 0:
            return None
        centroid = [0.0] * dim
        for vec in history:
            for i, v in enumerate(vec):
                centroid[i] += v
        n = float(len(history))
        return [x / n for x in centroid]

    def update_and_score(
        self,
        vertex_embedding: List[float],
        minilm_embedding: List[float],
    ) -> DriftResult:
        # # Update history with new embeddings and compute drift scores
        vertex_centroid = self._baseline_centroid(self._vertex_history)
        minilm_centroid = self._baseline_centroid(self._minilm_history)

        if vertex_centroid is None:
            vertex_drift = 0.0
        else:
            vertex_drift = _cosine_distance(vertex_embedding, vertex_centroid)

        if minilm_centroid is None:
            minilm_drift = 0.0
        else:
            minilm_drift = _cosine_distance(minilm_embedding, minilm_centroid)

        # # Hybrid score as simple average of Vertex and MiniLM drift
        hybrid_score = 0.5 * (vertex_drift + minilm_drift)

        # # Push new embeddings into history after scoring
        self._vertex_history.append(vertex_embedding)
        self._minilm_history.append(minilm_embedding)

        is_drift = hybrid_score >= self._drift_threshold

        return DriftResult(
            window_size=len(self._vertex_history),
            hybrid_drift_score=hybrid_score,
            vertex_drift_score=vertex_drift,
            minilm_drift_score=minilm_drift,
            is_drift=is_drift,
        )

    def current_baselines(self) -> Tuple[Optional[List[float]], Optional[List[float]]]:
        # # Return current centroid baselines for Vertex and MiniLM
        return (
            self._baseline_centroid(self._vertex_history),
            self._baseline_centroid(self._minilm_history),
        )

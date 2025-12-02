# Computes embedding-based drift scores
from typing import Protocol, List
from app.observability.analysis.drift_detector import DriftResult

class IEmbeddingDriftDetector(Protocol):
    # Updates the internal baseline and returns drift evaluation
    def update_and_score(
        self,
        vertex_vec: List[float],
        minilm_vec: List[float],
    ) -> DriftResult:
        ...

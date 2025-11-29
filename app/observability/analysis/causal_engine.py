from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Iterable, Optional
import math


@dataclass
class CausalEdge:
    # # Directed edge in a causal graph with an associated strength score
    source: str
    target: str
    weight: float


@dataclass
class CausalGraph:
    # # Simple representation of a causal graph as a list of edges
    edges: List[CausalEdge]

    def top_k_causes(self, target: str, k: int = 3) -> List[CausalEdge]:
        # # Return the k strongest incoming edges for a target variable
        incoming = [e for e in self.edges if e.target == target]
        incoming.sort(key=lambda e: abs(e.weight), reverse=True)
        return incoming[: max(0, k)]


class NotearsLiteCausalEngine:
    # # Lightweight causal engine inspired by NOTEARS for metric level RCA
    def __init__(self, l2_penalty: float = 1e-3) -> None:
        # # l2_penalty stabilizes the linear fit for noisy data
        self._l2_penalty = max(0.0, l2_penalty)

    def _standardize(self, series: List[float]) -> List[float]:
        # # Standardize series to zero mean and unit variance
        n = len(series)
        if n == 0:
            return []
        mean = sum(series) / float(n)
        var = sum((x - mean) * (x - mean) for x in series) / float(n)
        std = math.sqrt(var)
        if std == 0.0:
            return [0.0] * n
        return [(x - mean) / std for x in series]

    def _fit_linear(
        self,
        x: List[float],
        y: List[float],
    ) -> float:
        # # Fit a simple linear model y = a * x using ridge regularization and return a
        if len(x) != len(y) or len(x) == 0:
            return 0.0
        n = float(len(x))
        sum_xx = 0.0
        sum_xy = 0.0
        for xi, yi in zip(x, y):
            sum_xx += xi * xi
            sum_xy += xi * yi
        denom = sum_xx + self._l2_penalty
        if denom == 0.0:
            return 0.0
        return sum_xy / denom

    def infer_causal_graph(
        self,
        data: Dict[str, Iterable[float]],
        max_parents_per_node: Optional[int] = None,
        min_weight_threshold: float = 0.05,
    ) -> CausalGraph:
        # # Infer a simple directed causal graph among variables based on pairwise linear influence
        standardized: Dict[str, List[float]] = {}
        for name, series in data.items():
            standardized[name] = self._standardize(list(series))

        variable_names = list(standardized.keys())
        edges: List[CausalEdge] = []

        for target in variable_names:
            y = standardized[target]
            candidate_edges: List[CausalEdge] = []
            for source in variable_names:
                if source == target:
                    continue
                x = standardized[source]
                if len(x) != len(y) or len(x) == 0:
                    continue
                weight = self._fit_linear(x, y)
                if abs(weight) >= min_weight_threshold:
                    candidate_edges.append(CausalEdge(source=source, target=target, weight=weight))

            if max_parents_per_node is not None and max_parents_per_node > 0:
                candidate_edges.sort(key=lambda e: abs(e.weight), reverse=True)
                candidate_edges = candidate_edges[:max_parents_per_node]

            edges.extend(candidate_edges)

        return CausalGraph(edges=edges)

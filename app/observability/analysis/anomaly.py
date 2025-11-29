from __future__ import annotations

from typing import Iterable, List
import math


def z_score_anomalies(
    values: Iterable[float],
    threshold: float = 3.0,
) -> List[bool]:
    # # Mark values as anomalies if their z-score exceeds the given threshold
    data = list(values)
    n = len(data)
    if n == 0:
        return []
    mean = sum(data) / float(n)
    var = sum((x - mean) * (x - mean) for x in data) / float(n)
    std = math.sqrt(var)
    if std == 0.0:
        return [False] * n
    result: List[bool] = []
    for x in data:
        z = abs((x - mean) / std)
        result.append(z >= threshold)
    return result


def mad_anomalies(
    values: Iterable[float],
    threshold: float = 3.5,
) -> List[bool]:
    # # Mark values as anomalies using Median Absolute Deviation (robust outlier detection)
    data = list(values)
    n = len(data)
    if n == 0:
        return []
    sorted_data = sorted(data)
    mid = n // 2
    if n % 2 == 1:
        median = sorted_data[mid]
    else:
        median = 0.5 * (sorted_data[mid - 1] + sorted_data[mid])

    abs_devs = [abs(x - median) for x in data]
    sorted_devs = sorted(abs_devs)
    if n % 2 == 1:
        mad = sorted_devs[mid]
    else:
        mad = 0.5 * (sorted_devs[mid - 1] + sorted_devs[mid])

    if mad == 0.0:
        return [False] * n

    result: List[bool] = []
    for dev in abs_devs:
        modified_z = 0.6745 * dev / mad
        result.append(modified_z >= threshold)
    return result


def embedding_delta_anomaly_score(
    current: List[float],
    previous: List[float],
) -> float:
    # # Compute a simple anomaly score based on the L2 distance between two embeddings
    if len(current) != len(previous) or len(current) == 0:
        return 0.0
    acc = 0.0
    for a, b in zip(current, previous):
        diff = a - b
        acc += diff * diff
    return math.sqrt(acc)

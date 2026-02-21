import math
from typing import List

def l2_to_confidence(dist: float, alpha: float = 0.35) -> float:
    """
    Convert FAISS L2 distance -> confidence in [0,1].
    Smaller distance => higher confidence.
    conf = exp(-alpha * dist)
    """
    if dist is None:
        return 0.0
    try:
        d = float(dist)
    except Exception:
        return 0.0
    conf = math.exp(-alpha * d)
    return max(0.0, min(conf, 1.0))

def average_confidence(distances: List[float], alpha: float = 0.35) -> float:
    if not distances:
        return 0.0
    confs = [l2_to_confidence(d, alpha=alpha) for d in distances]
    return sum(confs) / len(confs)

def top_confidence(distances: List[float], alpha: float = 0.35) -> float:
    if not distances:
        return 0.0
    return max(l2_to_confidence(d, alpha=alpha) for d in distances)
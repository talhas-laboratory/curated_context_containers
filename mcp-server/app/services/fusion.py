"""Reciprocal rank fusion helpers."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List


def reciprocal_rank_fusion(
    rankings: Iterable[List[str]],
    k: int = 60,
) -> Dict[str, float]:
    """Compute RRF scores given ordered lists of chunk ids."""
    scores: Dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for idx, chunk_id in enumerate(ranking):
            scores[chunk_id] += 1.0 / (k + idx + 1)
    return scores

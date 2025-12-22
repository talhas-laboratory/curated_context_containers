"""Utilities for building search diagnostics responses."""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Dict, List


@dataclass
class StageTiming:
    label: str
    started_at: float
    duration_ms: int = 0

    def stop(self) -> None:
        self.duration_ms = int((perf_counter() - self.started_at) * 1000)


def stage_timer(label: str) -> StageTiming:
    return StageTiming(label=label, started_at=perf_counter())


def summarize_timings(stages: List[StageTiming]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for stage in stages:
        summary[f"{stage.label}_ms"] = stage.duration_ms
    summary["total_ms"] = sum(stage.duration_ms for stage in stages)
    return summary


def baseline_diagnostics(mode: str, containers: List[str]) -> dict:
    return {
        "mode": mode,
        "containers": containers,
        "bm25_hits": 0,
        "vector_hits": 0,
        "graph_hits": 0,
        "latency_budget_ms": 0,
        "latency_over_budget_ms": 0,
    }

from app.adapters.rerank import rerank_adapter
from app.models.search import SearchResult


def _cand(idx: int) -> SearchResult:
    return SearchResult(
        chunk_id=f"chunk-{idx}",
        doc_id=f"doc-{idx}",
        container_id="c-1",
        container_name="c-1",
        title=f"title-{idx}",
        snippet=f"snippet-{idx}",
        uri="",
        score=1.0,
        stage_scores={},
        modality="text",
        provenance={},
        meta={},
    )


import pytest


@pytest.mark.asyncio
async def test_rerank_disabled_provider_fallback():
    candidates = [_cand(i) for i in range(5)]
    ranked, diagnostics, issues = await rerank_adapter.rerank(
        query="test",
        candidates=candidates,
        top_k_in=3,
        top_k_out=2,
    )
    # Should preserve deterministic order, trimming to top_k_out and appending remainder.
    assert [c.chunk_id for c in ranked[:2]] == ["chunk-0", "chunk-1"]
    assert diagnostics["rerank_applied"] is False
    assert diagnostics["rerank_provider"] == "disabled"
    assert issues == []


@pytest.mark.asyncio
async def test_rerank_clamps_top_k_bounds():
    candidates = [_cand(i) for i in range(2)]
    ranked, diagnostics, issues = await rerank_adapter.rerank(
        query="test",
        candidates=candidates,
        top_k_in=10,  # larger than available
        top_k_out=5,
    )
    assert len(ranked) == 2  # cannot exceed available candidates
    assert diagnostics["rerank_top_k_in"] >= len(candidates)
    assert diagnostics["rerank_top_k_out"] >= 1
    assert issues == []

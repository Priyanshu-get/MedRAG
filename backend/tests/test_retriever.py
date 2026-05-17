"""
Tests for the hybrid retriever: RRF merging, deduplication, normalization.
"""
from __future__ import annotations

import pytest


def test_reciprocal_rank_fusion_merges_lists():
    """RRF should merge two ranked lists and score items appearing in both higher."""
    from app.rag.retriever import _reciprocal_rank_fusion

    list1 = [
        {"chunk_id": "a", "text": "ACE inhibitors"},
        {"chunk_id": "b", "text": "thiazide diuretics"},
        {"chunk_id": "c", "text": "beta blockers"},
    ]
    list2 = [
        {"chunk_id": "b", "text": "thiazide diuretics"},  # in both lists
        {"chunk_id": "d", "text": "calcium channel blockers"},
        {"chunk_id": "a", "text": "ACE inhibitors"},      # in both lists
    ]

    merged = _reciprocal_rank_fusion([list1, list2])
    chunk_ids = [m["chunk_id"] for m in merged]

    # Items appearing in both lists should be ranked highest
    assert chunk_ids.index("a") < chunk_ids.index("c")  # a is in both, c only in list1
    assert chunk_ids.index("b") < chunk_ids.index("d")  # b is in both, d only in list2


def test_reciprocal_rank_fusion_empty_lists():
    """RRF should handle empty input gracefully."""
    from app.rag.retriever import _reciprocal_rank_fusion

    result = _reciprocal_rank_fusion([[], []])
    assert result == []


def test_deduplicate_removes_duplicates():
    """Deduplication should remove chunks with the same chunk_id, keeping first."""
    from app.rag.retriever import _deduplicate

    chunks = [
        {"chunk_id": "a", "rrf_score": 0.9, "text": "first occurrence"},
        {"chunk_id": "b", "rrf_score": 0.8, "text": "unique b"},
        {"chunk_id": "a", "rrf_score": 0.7, "text": "duplicate a"},  # should be dropped
    ]
    result = _deduplicate(chunks)
    assert len(result) == 2
    assert result[0]["chunk_id"] == "a"
    assert result[0]["text"] == "first occurrence"  # kept first


def test_normalize_pg_row():
    """PostgreSQL row should be normalized to standard chunk dict format."""
    from app.rag.retriever import _normalize_pg_row

    row = {
        "chunk_id":    "pubmed_123_0",
        "chunk_text":  "ACE inhibitors are first-line agents.",
        "rank":        0.75,
        "title":       "Hypertension Guidelines",
        "pmid":        "123",
        "doi":         "10.1001/jama.2014.1",
        "authors":     ["Smith J", "Jones K"],
        "journal":     "JAMA",
        "pub_date":    "2014",
        "abstract":    "Abstract text.",
        "source_type": "pubmed",
        "url":         None,
        "pmc_id":      None,
    }
    normalized = _normalize_pg_row(row)

    assert normalized["chunk_id"] == "pubmed_123_0"
    assert normalized["text"] == "ACE inhibitors are first-line agents."
    assert normalized["similarity_score"] == 0.75
    assert normalized["metadata"]["title"] == "Hypertension Guidelines"
    assert normalized["metadata"]["authors"] == ["Smith J", "Jones K"]


@pytest.mark.asyncio
async def test_hybrid_retrieve_returns_empty_on_db_errors():
    """Retriever should return empty list gracefully when both DB calls fail."""
    from unittest.mock import AsyncMock, patch

    with (
        patch("app.rag.retriever.embed_single", new_callable=AsyncMock, side_effect=Exception("embedding failed")),
        patch("app.rag.retriever.pg_fulltext_search", new_callable=AsyncMock, side_effect=Exception("db error")),
    ):
        from app.rag.retriever import hybrid_retrieve
        result = await hybrid_retrieve(["hypertension treatment"], top_k=5)

    assert isinstance(result, list)
    assert len(result) == 0

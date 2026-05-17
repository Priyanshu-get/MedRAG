"""
Integration tests for the full RAG pipeline.
Uses mocked LLM and DB calls to test pipeline logic without live services.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_guard_response(has_answer: bool, confidence: float, reasoning: str) -> MagicMock:
    mock_content = MagicMock()
    mock_content.text = json.dumps({
        "has_answer": has_answer,
        "confidence": confidence,
        "reasoning": reasoning,
    })
    mock_resp = MagicMock()
    mock_resp.content = [mock_content]
    return mock_resp


def _make_answer_response(answer_text: str) -> MagicMock:
    mock_content = MagicMock()
    mock_content.text = answer_text
    mock_resp = MagicMock()
    mock_resp.content = [mock_content]
    return mock_resp


@pytest.mark.asyncio
async def test_pipeline_returns_no_answer_on_zero_retrieval():
    """When retrieval returns 0 chunks, pipeline must return has_answer=False."""
    with (
        patch("app.rag.pipeline.rewrite_query", return_value=["hypertension treatment"]),
        patch("app.rag.pipeline.hybrid_retrieve", new_callable=AsyncMock, return_value=[]),
        patch("app.rag.pipeline.get_cached_response", new_callable=AsyncMock, return_value=None),
        patch("app.rag.pipeline.cache_response", new_callable=AsyncMock),
    ):
        from app.rag.pipeline import run_rag_pipeline

        result = await run_rag_pipeline("What is the treatment for hypertension?")

    assert result.has_answer is False
    assert result.confidence == 0.0
    assert len(result.sources) == 0
    assert "No relevant medical literature" in result.answer or "unable" in result.answer.lower()


@pytest.mark.asyncio
async def test_pipeline_returns_no_answer_when_guard_rejects(sample_chunks):
    """When hallucination guard returns can_answer=False, pipeline must refuse."""
    guard_response = _make_guard_response(False, 0.3, "Context is only tangentially related.")

    with (
        patch("app.rag.pipeline.rewrite_query", return_value=["query"]),
        patch("app.rag.pipeline.hybrid_retrieve", new_callable=AsyncMock, return_value=sample_chunks),
        patch("app.rag.pipeline.rerank_chunks", return_value=sample_chunks),
        patch("app.rag.pipeline.build_context", return_value=("some context", sample_chunks)),
        patch("app.rag.pipeline.get_cached_response", new_callable=AsyncMock, return_value=None),
        patch("app.rag.pipeline.cache_response", new_callable=AsyncMock),
        patch("app.rag.hallucination_guard.get_client") as mock_get_client,
    ):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=guard_response)
        mock_get_client.return_value = mock_client

        from app.rag.pipeline import run_rag_pipeline

        result = await run_rag_pipeline("What is the dosage of metformin?")

    assert result.has_answer is False
    assert result.confidence < 0.5
    assert len(result.sources) == 0


@pytest.mark.asyncio
async def test_pipeline_returns_grounded_answer_with_citations(sample_chunks, relevant_context):
    """When all stages pass, pipeline returns a grounded answer with citations."""
    guard_response    = _make_guard_response(True, 0.87, "Context directly addresses the query.")
    answer_with_citations = (
        "ACE inhibitors are the first-line treatment for hypertension in diabetic patients [Source 1]. "
        "Thiazide diuretics are recommended for uncomplicated hypertension [Source 2]."
    )
    answer_response = _make_answer_response(answer_with_citations)

    with (
        patch("app.rag.pipeline.rewrite_query", return_value=["hypertension treatment ACE inhibitors"]),
        patch("app.rag.pipeline.hybrid_retrieve", new_callable=AsyncMock, return_value=sample_chunks),
        patch("app.rag.pipeline.rerank_chunks", return_value=sample_chunks),
        patch("app.rag.pipeline.build_context", return_value=(relevant_context, sample_chunks)),
        patch("app.rag.pipeline.get_cached_response", new_callable=AsyncMock, return_value=None),
        patch("app.rag.pipeline.cache_response", new_callable=AsyncMock),
        patch("app.rag.hallucination_guard.get_client") as mock_guard_client,
        patch("app.rag.answer_generator.get_client") as mock_answer_client,
    ):
        mock_guard = AsyncMock()
        mock_guard.messages.create = AsyncMock(return_value=guard_response)
        mock_guard_client.return_value = mock_guard

        mock_answer = AsyncMock()
        mock_answer.messages.create = AsyncMock(return_value=answer_response)
        mock_answer_client.return_value = mock_answer

        from app.rag.pipeline import run_rag_pipeline
        # Reload to get fresh import
        import importlib
        import app.rag.pipeline as pipeline_module
        importlib.reload(pipeline_module)

        result = await pipeline_module.run_rag_pipeline(
            "What is the first-line treatment for hypertension?"
        )

    assert result.has_answer is True
    assert result.confidence >= 0.65
    assert len(result.sources) > 0
    assert result.disclaimer != ""
    assert "[Source" in result.answer or "Source" in result.answer


@pytest.mark.asyncio
async def test_pipeline_always_includes_disclaimer(sample_chunks):
    """Every response (success or no-answer) must include the medical disclaimer."""
    with (
        patch("app.rag.pipeline.rewrite_query", return_value=["query"]),
        patch("app.rag.pipeline.hybrid_retrieve", new_callable=AsyncMock, return_value=[]),
        patch("app.rag.pipeline.get_cached_response", new_callable=AsyncMock, return_value=None),
        patch("app.rag.pipeline.cache_response", new_callable=AsyncMock),
    ):
        from app.rag.pipeline import run_rag_pipeline

        result = await run_rag_pipeline("some query")

    assert result.disclaimer != ""
    assert "NOT a substitute" in result.disclaimer or "not a substitute" in result.disclaimer.lower()

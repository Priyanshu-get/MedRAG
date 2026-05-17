"""
Tests for the Hallucination Guard — the most critical pipeline component.
Validates that the guard correctly identifies sufficient vs. insufficient context.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Unit tests (mocked LLM) ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_guard_returns_false_for_empty_context():
    """Empty context must always return can_answer=False with confidence=0."""
    from app.rag.hallucination_guard import validate_context

    result = await validate_context(
        query="What is the treatment for hypertension?",
        context="",
    )
    assert result["can_answer"] is False
    assert result["confidence"] == 0.0


@pytest.mark.asyncio
async def test_guard_returns_false_for_irrelevant_context(irrelevant_context):
    """
    Context about photosynthesis cannot answer a medical query.
    Guard should return can_answer=False.
    """
    mock_response_text = json.dumps({
        "has_answer": False,
        "confidence": 0.05,
        "reasoning": "The context is about photosynthesis, not hypertension treatment.",
    })

    mock_content = MagicMock()
    mock_content.text = mock_response_text
    mock_response = MagicMock()
    mock_response.content = [mock_content]

    with patch(
        "app.rag.hallucination_guard.get_client"
    ) as mock_get_client:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await validate_context(
            query="What is the first-line treatment for hypertension?",
            context=irrelevant_context,
        )

    assert result["can_answer"] is False
    assert result["confidence"] < 0.5


@pytest.mark.asyncio
async def test_guard_returns_true_for_relevant_context(relevant_context):
    """
    Context directly addressing hypertension treatment should pass the guard.
    """
    mock_response_text = json.dumps({
        "has_answer": True,
        "confidence": 0.88,
        "reasoning": "Context directly states ACE inhibitors and thiazide diuretics as first-line agents.",
    })

    mock_content = MagicMock()
    mock_content.text = mock_response_text
    mock_response = MagicMock()
    mock_response.content = [mock_content]

    with patch(
        "app.rag.hallucination_guard.get_client"
    ) as mock_get_client:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await validate_context(
            query="What is the first-line treatment for hypertension?",
            context=relevant_context,
        )

    assert result["can_answer"] is True
    assert result["confidence"] >= 0.65


@pytest.mark.asyncio
async def test_guard_enforces_confidence_below_half_for_false():
    """When has_answer=False, confidence must be forced below 0.5 even if LLM returns higher."""
    mock_response_text = json.dumps({
        "has_answer": False,
        "confidence": 0.75,   # Invalid — should be forced below 0.5
        "reasoning": "Context is only tangentially related.",
    })

    mock_content = MagicMock()
    mock_content.text = mock_response_text
    mock_response = MagicMock()
    mock_response.content = [mock_content]

    with patch(
        "app.rag.hallucination_guard.get_client"
    ) as mock_get_client:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await validate_context(
            query="What is the mechanism of action of metformin?",
            context="Insulin resistance is a hallmark of type 2 diabetes.",
        )

    assert result["can_answer"] is False
    assert result["confidence"] < 0.5


@pytest.mark.asyncio
async def test_guard_fails_safely_on_llm_error():
    """If LLM call fails, guard should return can_answer=False (conservative default)."""
    with patch(
        "app.rag.hallucination_guard.get_client"
    ) as mock_get_client:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API timeout"))
        mock_get_client.return_value = mock_client

        result = await validate_context(
            query="What is the treatment for sepsis?",
            context="Broad-spectrum antibiotics are used in sepsis management.",
        )

    assert result["can_answer"] is False
    assert result["confidence"] == 0.0


# ── Hallucination stress tests ────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("fictional_query", [
    "What is the cure for Blorbitis disease?",
    "What is the mechanism of action of Zanthoximab?",
    "How does Fibromyxotosis affect the pancreas?",
    "What is the standard protocol for treating Kreutz syndrome?",
])
async def test_guard_rejects_fictional_medical_queries(fictional_query):
    """
    Out-of-domain queries (fictional diseases/drugs) must always return can_answer=False.
    The context will be empty/irrelevant for fictional topics.
    """
    # Empty context simulates zero retrieval for unknown topics
    result = await validate_context(
        query=fictional_query,
        context="",
    )
    assert result["can_answer"] is False, (
        f"Guard should reject fictional query: '{fictional_query}'"
    )

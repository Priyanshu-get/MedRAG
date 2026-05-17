"""
MedRAG Pipeline Orchestrator — ties all 7 RAG stages together.

Stage 1: Query Rewriter      → expand to MeSH-optimized queries
Stage 2: Hybrid Retriever    → dense (Qdrant) + sparse (PostgreSQL FTS) + RRF
Stage 3: Re-Ranker           → cross-encoder precision scoring
Stage 4: Context Builder     → assemble numbered citation blocks
Stage 5: Hallucination Guard → LLM-as-judge validates context sufficiency
Stage 6: Answer Generator    → strictly evidence-bound LLM answer
Stage 7: Citation Injector   → format sources into SourceMetadata objects

Zero-hallucination architecture:
  • Early exit at Stage 2 if 0 chunks retrieved
  • Early exit at Stage 5 if guard confidence < HALLUCINATION_CONFIDENCE_THRESHOLD
  • Layer 4: post-generation citation count check in answer_generator
  • Medical disclaimer appended to every response
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Dict, List, Optional

from app.config import settings
from app.db.cache import cache_response, get_cached_response
from app.models.response import ChatResponse, SourceMetadata
from app.rag.answer_generator import generate_answer
from app.rag.citation_injector import build_source_metadata, format_answer_with_links
from app.rag.context_builder import build_context
from app.rag.hallucination_guard import validate_context
from app.rag.query_rewriter import rewrite_query
from app.rag.reranker import rerank_chunks
from app.rag.retriever import hybrid_retrieve

logger = logging.getLogger(__name__)

MEDICAL_DISCLAIMER = (
    "This response is derived solely from indexed peer-reviewed literature. "
    "It is NOT a substitute for professional medical advice, diagnosis, or treatment. "
    "Always consult a qualified healthcare professional."
)

# ── No-answer templates (Layer 6) ────────────────────────────────────────────

def _no_answer_zero_retrieval() -> str:
    return (
        "No relevant medical literature was found for this query in our indexed databases. "
        "This may indicate the topic is not yet indexed or the query is outside the medical domain. "
        "Please consult a licensed medical professional or try a more specific clinical query."
    )


def _no_answer_low_confidence(confidence: float, reasoning: str) -> str:
    return (
        f"The retrieved evidence does not directly address this question with sufficient specificity "
        f"(confidence: {confidence:.0%}). "
        f"{reasoning} "
        f"Please consult a licensed medical professional or refine your query with "
        f"more specific clinical terminology."
    )


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def run_rag_pipeline(
    user_query: str,
    max_sources: int = 5,
    use_cache: bool = True,
) -> ChatResponse:
    """
    Execute the full 7-stage MedRAG pipeline.

    Returns a ChatResponse with grounded answer + citations,
    or a no-answer response if evidence is insufficient.
    """
    start_time = time.monotonic()

    # ── Cache check ───────────────────────────────────────────────────────────
    if use_cache:
        cached = await get_cached_response(user_query)
        if cached:
            logger.info("Cache hit for query (%.0fms)", (time.monotonic() - start_time) * 1000)
            return ChatResponse(**cached)

    logger.info("Pipeline start: '%s'", user_query[:80])

    # ── Stage 1: Query Rewriting ──────────────────────────────────────────────
    t1 = time.monotonic()
    expanded_queries = await rewrite_query(user_query)
    logger.info("Stage 1 (rewrite): %d queries in %.0fms", len(expanded_queries), (time.monotonic() - t1) * 1000)

    # ── Stage 2: Hybrid Retrieval ─────────────────────────────────────────────
    t2 = time.monotonic()
    retrieved_chunks = await hybrid_retrieve(
        queries=expanded_queries,
        top_k=settings.max_retrieved_chunks,
        score_threshold=settings.similarity_threshold,
    )
    logger.info("Stage 2 (retrieve): %d chunks in %.0fms", len(retrieved_chunks), (time.monotonic() - t2) * 1000)

    # Early exit: zero retrieval
    if not retrieved_chunks:
        logger.info("Pipeline exit: zero chunks retrieved")
        return _build_no_answer_response(
            query=user_query,
            answer=_no_answer_zero_retrieval(),
            confidence=0.0,
        )

    # ── Stage 3: Re-Ranking ───────────────────────────────────────────────────
    t3 = time.monotonic()
    top_chunks = rerank_chunks(
        query=user_query,
        chunks=retrieved_chunks,
        top_k=settings.rerank_top_k,
    )
    logger.info("Stage 3 (rerank): %d→%d chunks in %.0fms", len(retrieved_chunks), len(top_chunks), (time.monotonic() - t3) * 1000)

    # ── Stage 4: Context Building ─────────────────────────────────────────────
    t4 = time.monotonic()
    context_str, included_chunks = build_context(top_chunks)
    logger.info("Stage 4 (context): %d included chunks in %.0fms", len(included_chunks), (time.monotonic() - t4) * 1000)

    # ── Stage 5: Hallucination Guard ──────────────────────────────────────────
    t5 = time.monotonic()
    guard_result = await validate_context(user_query, context_str)
    logger.info(
        "Stage 5 (guard): can_answer=%s, confidence=%.2f in %.0fms",
        guard_result["can_answer"], guard_result["confidence"], (time.monotonic() - t5) * 1000,
    )

    if not guard_result["can_answer"]:
        return _build_no_answer_response(
            query=user_query,
            answer=_no_answer_low_confidence(
                guard_result["confidence"], guard_result.get("reasoning", "")
            ),
            confidence=guard_result["confidence"],
        )

    # ── Stage 6: Answer Generation ────────────────────────────────────────────
    t6 = time.monotonic()
    gen_result = await generate_answer(user_query, included_chunks)
    logger.info("Stage 6 (generate): %d citations in %.0fms", gen_result["citation_count"], (time.monotonic() - t6) * 1000)

    # ── Stage 7: Citation Injection ───────────────────────────────────────────
    t7 = time.monotonic()
    answer_text  = gen_result["answer"]
    sources_meta = build_source_metadata(included_chunks, answer_text)
    answer_html  = format_answer_with_links(answer_text)
    logger.info("Stage 7 (citations): %d sources in %.0fms", len(sources_meta), (time.monotonic() - t7) * 1000)

    # ── Assemble response ─────────────────────────────────────────────────────
    total_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "Pipeline complete: has_answer=True, %d sources, %.0fms total",
        len(sources_meta), total_ms,
    )

    response = ChatResponse(
        query=user_query,
        answer=answer_html,
        sources=sources_meta[:max_sources],
        confidence=round(guard_result["confidence"], 3),
        has_answer=True,
        source_count=len(sources_meta),
        disclaimer=MEDICAL_DISCLAIMER,
    )

    # Cache successful responses
    if use_cache:
        await cache_response(user_query, response.model_dump())

    return response


def _build_no_answer_response(
    query: str,
    answer: str,
    confidence: float,
) -> ChatResponse:
    return ChatResponse(
        query=query,
        answer=answer,
        sources=[],
        confidence=round(confidence, 3),
        has_answer=False,
        source_count=0,
        disclaimer=MEDICAL_DISCLAIMER,
    )

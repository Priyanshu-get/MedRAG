"""
/api/v1/chat — Main chat endpoint.
Accepts a medical query and returns a grounded, cited answer.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models.query import QueryRequest
from app.models.response import ChatResponse
from app.rag.pipeline import run_rag_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Submit a medical query",
    description=(
        "Runs the full 7-stage RAG pipeline:\n"
        "1. Query rewriting\n"
        "2. Hybrid retrieval (dense + sparse)\n"
        "3. Cross-encoder re-ranking\n"
        "4. Context assembly\n"
        "5. Hallucination guard (LLM-as-judge)\n"
        "6. Grounded answer generation\n"
        "7. Citation injection\n\n"
        "Returns `has_answer: false` with an explanation when evidence is insufficient."
    ),
)
async def chat(request: QueryRequest) -> ChatResponse:
    """Submit a medical query and receive a grounded, cited response."""
    logger.info("Chat request: '%s' (session=%s)", request.query[:80], request.session_id)

    try:
        result = await run_rag_pipeline(
            user_query=request.query,
            max_sources=request.max_sources,
        )
        return result

    except Exception as exc:
        logger.error("Chat endpoint unhandled error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing your query. Please try again.",
        )

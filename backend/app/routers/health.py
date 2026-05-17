"""
/api/v1/health — Service health check endpoint.
Reports status of all downstream dependencies.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.cache import check_redis_health
from app.db.postgres import check_postgres_health, count_indexed_documents
from app.db.vector_store import check_qdrant_health, count_vectors
from app.models.response import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
)
async def health() -> HealthResponse:
    """Check the health of all downstream services."""
    qdrant_ok   = await check_qdrant_health()
    postgres_ok = await check_postgres_health()
    redis_ok    = await check_redis_health()

    indexed_docs = 0
    if qdrant_ok:
        try:
            indexed_docs = await count_vectors()
        except Exception:
            pass

    all_healthy = qdrant_ok and postgres_ok and redis_ok

    response = HealthResponse(
        status="healthy" if all_healthy else "degraded",
        qdrant="ok" if qdrant_ok else "unavailable",
        postgres="ok" if postgres_ok else "unavailable",
        redis="ok" if redis_ok else "unavailable",
        embedding_provider=settings.embedding_provider,
        llm_model=settings.llm_model,
        indexed_documents=indexed_docs,
    )

    if not all_healthy:
        logger.warning("Health check: degraded — %s", response.model_dump())

    return response

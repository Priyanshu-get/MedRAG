"""
MedRAG FastAPI Application Entry Point
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info("🚀 MedRAG API starting up — environment: %s", settings.app_env)

    # Initialize Qdrant collection
    try:
        from app.db.vector_store import init_qdrant_collection
        await init_qdrant_collection()
        logger.info("✅ Qdrant collection ready: %s", settings.qdrant_collection)
    except Exception as exc:
        logger.warning(
            "⚠️  Qdrant unavailable at startup (will retry on first request): %s", exc
        )

    # Warm up reranker model
    try:
        from app.rag.reranker import warm_up_reranker
        warm_up_reranker()
        logger.info("✅ Reranker model loaded")
    except Exception as exc:
        logger.warning("⚠️  Reranker warm-up failed: %s", exc)

    yield

    logger.info("👋 MedRAG API shutting down")


app = FastAPI(
    title="MedRAG API",
    description=(
        "**Hallucination-free medical evidence retrieval system.**\n\n"
        "All answers are grounded exclusively in indexed peer-reviewed literature. "
        "If no relevant evidence is found, the system explicitly states it does not know."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
from app.routers import chat, ingest, health  # noqa: E402

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(chat.router,   prefix="/api/v1", tags=["Chat"])
app.include_router(ingest.router, prefix="/api/v1", tags=["Ingestion"])


# ── Root ───────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"], include_in_schema=False)
async def root():
    return {
        "service": "MedRAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "status": "operational",
    }


# ── Global exception handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )

"""
MedRAG Application Configuration
All settings loaded from environment variables / .env file.
"""
from __future__ import annotations

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM ────────────────────────────────────────────
    gemini_api_key: str = ""
    openai_api_key: str = ""            # Only needed if EMBEDDING_PROVIDER=openai
    llm_model: str = "gemini-2.0-flash"

    # ── Embeddings ─────────────────────────────────────
    embedding_provider: str = "local"            # "openai" | "local"
    openai_embedding_model: str = "text-embedding-3-large"
    local_embedding_model: str = "BAAI/bge-small-en-v1.5"
    qdrant_vector_size: int = 384               # 3072 for OpenAI, 384 for bge-small/MiniLM

    # ── Qdrant ─────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "medrag_docs"

    # ── PostgreSQL ─────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://medrag_user:medrag_pass@localhost:5432/medrag"
    )

    # ── Redis ──────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 3600

    # ── NCBI / PubMed ──────────────────────────────────
    ncbi_api_key: str = ""
    ncbi_email: str = "medrag@example.com"

    # ── Anthropic (legacy — no longer used) ────────────
    anthropic_api_key: str = ""         # kept for backward compat

    # ── Semantic Scholar ───────────────────────────────────
    semantic_scholar_api_key: str = ""

    # ── RAG Pipeline ───────────────────────────────────────
    max_retrieved_chunks: int = 20
    rerank_top_k: int = 5
    similarity_threshold: float = 0.72
    hallucination_confidence_threshold: float = 0.65
    max_context_tokens: int = 8000

    # ── App ────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()

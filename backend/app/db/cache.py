"""
Redis async client for query result caching.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
        )
    return _redis


def _cache_key(query: str) -> str:
    """Deterministic cache key from the query string."""
    import hashlib
    digest = hashlib.sha256(query.lower().strip().encode()).hexdigest()
    return f"medrag:query:{digest}"


async def get_cached_response(query: str) -> Optional[dict]:
    """Return cached response dict or None if cache miss."""
    try:
        r = get_redis()
        raw = await r.get(_cache_key(query))
        if raw:
            logger.debug("Cache HIT for query (hash %s)", _cache_key(query)[:12])
            return json.loads(raw)
        return None
    except Exception as exc:
        logger.warning("Redis cache GET failed: %s", exc)
        return None


async def cache_response(query: str, response: dict, ttl: int | None = None) -> None:
    """Store a response dict in Redis with TTL."""
    try:
        r = get_redis()
        await r.setex(
            _cache_key(query),
            ttl or settings.cache_ttl_seconds,
            json.dumps(response, default=str),
        )
        logger.debug("Cached response for query (hash %s)", _cache_key(query)[:12])
    except Exception as exc:
        logger.warning("Redis cache SET failed: %s", exc)


async def check_redis_health() -> bool:
    """Return True if Redis is reachable."""
    try:
        r = get_redis()
        await r.ping()
        return True
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        return False

"""
Cliente Redis async (Upstash) — singleton.

Patrón idéntico al AppSheet client: lazy init, shutdown en lifespan.
Si redis_url no está configurado, get_redis() devuelve None y todo
funciona sin cache/lock (degradación graceful).
"""

from __future__ import annotations

from typing import Optional

from src.config import get_settings
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

_client: Optional["redis.asyncio.Redis"] = None  # type: ignore[name-defined]


async def get_redis() -> Optional["redis.asyncio.Redis"]:  # type: ignore[name-defined]
    """
    Devuelve el cliente Redis async (singleton).

    - Si redis_url no está configurado → None (graceful degradation).
    - Si Redis no responde → None (log warning, no crash).
    - Lazy init: se conecta en el primer uso.
    """
    global _client

    if _client is not None:
        return _client

    settings = get_settings()
    if not settings.redis_url:
        logger.debug("redis_not_configured")
        return None

    try:
        import redis.asyncio as aioredis

        _client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        # Verificar conexión
        await _client.ping()
        logger.info("redis_connected")
        return _client
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
        _client = None
        return None


async def shutdown_redis() -> None:
    """Cierra la conexión Redis. Llamar desde lifespan shutdown."""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
            logger.info("redis_closed")
        except Exception as e:
            logger.warning("redis_close_error", error=str(e))
        finally:
            _client = None


async def ping_redis() -> bool:
    """Health check: intenta ping a Redis. Retorna True/False."""
    client = await get_redis()
    if client is None:
        return False
    try:
        return await client.ping()
    except Exception:
        return False

"""
Lock por conversación + cola de mensajes (Redis).

Garantiza que solo un proceso maneje mensajes de un teléfono a la vez.
Si otro mensaje llega mientras se procesa, se encola en Redis y se
procesa en orden FIFO cuando el lock holder termina.

Degradación graceful: si Redis no está disponible, las funciones
retornan valores que hacen que el mensaje se procese directamente
(comportamiento actual sin lock).
"""

from __future__ import annotations

import json
from typing import Optional
from uuid import uuid4

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Lua script para release atómico: solo el owner puede liberar
_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


def generate_owner_id() -> str:
    """Genera un ID único para el owner del lock."""
    return str(uuid4())


async def acquire_lock(phone: str, owner_id: str, ttl: int = 120) -> bool:
    """
    Intenta adquirir el lock para una conversación.

    Args:
        phone: Teléfono normalizado (10 dígitos).
        owner_id: UUID del proceso que quiere el lock.
        ttl: Segundos de auto-expiración (protección anti-deadlock).

    Returns:
        True si se adquirió el lock, False si ya está ocupado.
        True si Redis no disponible (graceful degradation).
    """
    try:
        from src.clients.redis_client import get_redis
        redis = await get_redis()
        if redis is None:
            # Sin Redis → procesar directamente (sin lock)
            return True

        key = f"lock:conv:{phone}"
        acquired = await redis.set(key, owner_id, ex=ttl, nx=True)

        if acquired:
            logger.debug("lock_acquired", phone=phone, owner=owner_id[:8])
        else:
            logger.debug("lock_busy", phone=phone, owner=owner_id[:8])

        return bool(acquired)
    except Exception as e:
        logger.warning("lock_acquire_error", phone=phone, error=str(e))
        return True  # Graceful: procesar sin lock


async def release_lock(phone: str, owner_id: str) -> bool:
    """
    Libera el lock solo si el owner coincide (atómico via Lua).

    Returns:
        True si se liberó, False si no era el owner o no existía.
    """
    try:
        from src.clients.redis_client import get_redis
        redis = await get_redis()
        if redis is None:
            return True

        key = f"lock:conv:{phone}"
        result = await redis.eval(_RELEASE_SCRIPT, 1, key, owner_id)
        released = bool(result)

        if released:
            logger.debug("lock_released", phone=phone, owner=owner_id[:8])
        else:
            logger.debug("lock_release_not_owner", phone=phone, owner=owner_id[:8])

        return released
    except Exception as e:
        logger.warning("lock_release_error", phone=phone, error=str(e))
        return False


async def enqueue_message(phone: str, message_data: dict) -> bool:
    """
    Encola un mensaje para procesamiento posterior (FIFO).

    Args:
        phone: Teléfono normalizado.
        message_data: Dict con content, message_type, wa_message_id, etc.

    Returns:
        True si se encoló exitosamente.
    """
    try:
        from src.clients.redis_client import get_redis
        redis = await get_redis()
        if redis is None:
            return False

        key = f"queue:conv:{phone}"
        await redis.rpush(key, json.dumps(message_data, default=str))
        # TTL en la cola para evitar mensajes zombies (10 min)
        await redis.expire(key, 600)

        logger.info("message_enqueued", phone=phone)
        return True
    except Exception as e:
        logger.warning("enqueue_error", phone=phone, error=str(e))
        return False


async def dequeue_message(phone: str) -> Optional[dict]:
    """
    Saca el próximo mensaje de la cola (FIFO).

    Returns:
        Dict con datos del mensaje, o None si la cola está vacía.
    """
    try:
        from src.clients.redis_client import get_redis
        redis = await get_redis()
        if redis is None:
            return None

        key = f"queue:conv:{phone}"
        data = await redis.lpop(key)
        if data:
            logger.info("message_dequeued", phone=phone)
            return json.loads(data)
        return None
    except Exception as e:
        logger.warning("dequeue_error", phone=phone, error=str(e))
        return None

"""
Tests del lock por conversación y cola de mensajes.
Verifica lock/unlock, cola FIFO, owner protection, y graceful degradation.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.services.conversation_lock import (
    acquire_lock,
    dequeue_message,
    enqueue_message,
    generate_owner_id,
    release_lock,
)


@pytest.fixture
def mock_redis():
    """Mock Redis async client para tests de lock."""
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.eval = AsyncMock(return_value=1)
    redis.rpush = AsyncMock()
    redis.expire = AsyncMock()
    redis.lpop = AsyncMock(return_value=None)
    return redis


# =============================================================================
# ACQUIRE LOCK
# =============================================================================

class TestAcquireLock:
    async def test_acquires_lock_successfully(self, mock_redis):
        """Lock libre → adquiere con SETNX."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await acquire_lock("1112345678", "owner-1", ttl=120)
            assert result is True
            mock_redis.set.assert_called_once_with(
                "lock:conv:1112345678", "owner-1", ex=120, nx=True,
            )

    async def test_lock_busy(self, mock_redis):
        """Lock ocupado → SETNX retorna None → False."""
        mock_redis.set = AsyncMock(return_value=None)
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await acquire_lock("1112345678", "owner-2")
            assert result is False

    async def test_graceful_without_redis(self):
        """Sin Redis → True (procesar directamente)."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=None):
            result = await acquire_lock("1112345678", "owner-1")
            assert result is True

    async def test_graceful_on_error(self, mock_redis):
        """Error de Redis → True (procesar directamente)."""
        mock_redis.set = AsyncMock(side_effect=Exception("Connection lost"))
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await acquire_lock("1112345678", "owner-1")
            assert result is True


# =============================================================================
# RELEASE LOCK
# =============================================================================

class TestReleaseLock:
    async def test_releases_lock_as_owner(self, mock_redis):
        """Owner correcto → libera lock (Lua eval retorna 1)."""
        mock_redis.eval = AsyncMock(return_value=1)
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await release_lock("1112345678", "owner-1")
            assert result is True

    async def test_fails_if_not_owner(self, mock_redis):
        """Owner incorrecto → Lua eval retorna 0 → False."""
        mock_redis.eval = AsyncMock(return_value=0)
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await release_lock("1112345678", "wrong-owner")
            assert result is False

    async def test_graceful_without_redis(self):
        """Sin Redis → True (noop)."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=None):
            result = await release_lock("1112345678", "owner-1")
            assert result is True


# =============================================================================
# ENQUEUE / DEQUEUE
# =============================================================================

class TestMessageQueue:
    async def test_enqueue_message(self, mock_redis):
        """Encola mensaje con RPUSH + TTL."""
        msg_data = {"content": "Hola", "message_type": "text", "wa_message_id": "wamid.001"}
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await enqueue_message("1112345678", msg_data)
            assert result is True
            mock_redis.rpush.assert_called_once()
            mock_redis.expire.assert_called_once_with("queue:conv:1112345678", 600)

    async def test_dequeue_message(self, mock_redis):
        """Desencola mensaje con LPOP."""
        msg_data = {"content": "Hola", "message_type": "text"}
        mock_redis.lpop = AsyncMock(return_value=json.dumps(msg_data))
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await dequeue_message("1112345678")
            assert result == msg_data
            mock_redis.lpop.assert_called_once_with("queue:conv:1112345678")

    async def test_dequeue_empty_queue(self, mock_redis):
        """Cola vacía → None."""
        mock_redis.lpop = AsyncMock(return_value=None)
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await dequeue_message("1112345678")
            assert result is None

    async def test_fifo_order(self, mock_redis):
        """Mensajes se procesan en orden FIFO."""
        messages = [
            {"content": "Primero", "wa_message_id": "1"},
            {"content": "Segundo", "wa_message_id": "2"},
            {"content": "Tercero", "wa_message_id": "3"},
        ]
        # Simular LPOP retornando en orden
        mock_redis.lpop = AsyncMock(side_effect=[
            json.dumps(messages[0]),
            json.dumps(messages[1]),
            json.dumps(messages[2]),
            None,  # Cola vacía
        ])
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            results = []
            while True:
                msg = await dequeue_message("1112345678")
                if msg is None:
                    break
                results.append(msg["content"])

            assert results == ["Primero", "Segundo", "Tercero"]

    async def test_enqueue_fails_without_redis(self):
        """Sin Redis → enqueue retorna False."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=None):
            result = await enqueue_message("1112345678", {"content": "test"})
            assert result is False

    async def test_dequeue_fails_without_redis(self):
        """Sin Redis → dequeue retorna None."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=None):
            result = await dequeue_message("1112345678")
            assert result is None


# =============================================================================
# OWNER ID
# =============================================================================

class TestGenerateOwnerId:
    def test_generates_unique_ids(self):
        """Cada llamada genera un ID diferente."""
        id1 = generate_owner_id()
        id2 = generate_owner_id()
        assert id1 != id2
        assert len(id1) == 36  # UUID format

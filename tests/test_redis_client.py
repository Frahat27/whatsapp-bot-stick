"""
Tests del cliente Redis async.
Verifica singleton, graceful degradation, y ping.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients import redis_client


# Reset singleton entre tests
@pytest.fixture(autouse=True)
def reset_redis_singleton():
    """Reset del singleton _client entre cada test."""
    redis_client._client = None
    yield
    redis_client._client = None


class TestGetRedis:
    async def test_returns_none_if_url_empty(self):
        """Sin redis_url configurado → None (graceful degradation)."""
        with patch("src.clients.redis_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(redis_url="")
            result = await redis_client.get_redis()
            assert result is None

    async def test_returns_client_on_success(self):
        """Con redis_url y ping exitoso → retorna cliente."""
        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping = AsyncMock(return_value=True)

        with patch("src.clients.redis_client.get_settings") as mock_settings, \
             patch("redis.asyncio.from_url", return_value=mock_redis_instance):
            mock_settings.return_value = MagicMock(redis_url="redis://localhost:6379")
            result = await redis_client.get_redis()
            assert result is mock_redis_instance

    async def test_returns_none_on_connection_error(self):
        """Si Redis no responde → None, no crash."""
        with patch("src.clients.redis_client.get_settings") as mock_settings, \
             patch("redis.asyncio.from_url", side_effect=Exception("Connection refused")):
            mock_settings.return_value = MagicMock(redis_url="redis://bad-host:6379")
            result = await redis_client.get_redis()
            assert result is None

    async def test_singleton_returns_same_client(self):
        """Segunda llamada devuelve el mismo cliente (singleton)."""
        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping = AsyncMock(return_value=True)

        with patch("src.clients.redis_client.get_settings") as mock_settings, \
             patch("redis.asyncio.from_url", return_value=mock_redis_instance) as mock_from_url:
            mock_settings.return_value = MagicMock(redis_url="redis://localhost:6379")

            client1 = await redis_client.get_redis()
            client2 = await redis_client.get_redis()

            assert client1 is client2
            # from_url solo se llamó 1 vez (singleton)
            mock_from_url.assert_called_once()


class TestShutdownRedis:
    async def test_closes_client(self):
        """shutdown_redis cierra el cliente y resetea singleton."""
        mock_client = AsyncMock()
        redis_client._client = mock_client

        await redis_client.shutdown_redis()

        mock_client.aclose.assert_called_once()
        assert redis_client._client is None

    async def test_noop_if_no_client(self):
        """shutdown_redis sin cliente → no falla."""
        await redis_client.shutdown_redis()  # No debe tirar error

    async def test_handles_close_error(self):
        """Si aclose falla → log warning, pero resetea singleton."""
        mock_client = AsyncMock()
        mock_client.aclose.side_effect = Exception("Close error")
        redis_client._client = mock_client

        await redis_client.shutdown_redis()
        assert redis_client._client is None


class TestPingRedis:
    async def test_returns_true_on_success(self):
        """ping_redis con Redis disponible → True."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        redis_client._client = mock_client

        result = await redis_client.ping_redis()
        assert result is True

    async def test_returns_false_if_no_redis(self):
        """ping_redis sin Redis → False."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=None):
            result = await redis_client.ping_redis()
            assert result is False

    async def test_returns_false_on_ping_error(self):
        """ping_redis con error de ping → False, no crash."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=Exception("Timeout"))
        redis_client._client = mock_client

        result = await redis_client.ping_redis()
        assert result is False

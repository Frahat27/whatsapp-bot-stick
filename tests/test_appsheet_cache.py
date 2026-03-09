"""
Tests del cache Redis en AppSheetClient.
Verifica cache hit, miss, invalidación, tablas estáticas, y graceful degradation.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.appsheet import AppSheetClient


@pytest.fixture
def mock_redis():
    """Mock Redis async client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def client():
    """AppSheetClient con HTTP y rate limit mockeados."""
    with patch("src.clients.appsheet.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            appsheet_app_id="test-app",
            appsheet_api_key="test-key",
            appsheet_min_interval_seconds=0,  # Sin delay en tests
        )
        c = AppSheetClient()
        # Mock HTTP client para evitar requests reales
        c._client = AsyncMock()
        return c


# =============================================================================
# CACHE PATIENT/LEAD
# =============================================================================

class TestPatientCache:
    async def test_cache_miss_then_hit(self, client, mock_redis):
        """Primera llamada → AppSheet + cache set. Segunda → cache hit."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            # Mock AppSheet response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '[{"Paciente": "Test"}]'
            mock_response.json.return_value = [{"Paciente": "Test"}]
            client._client.post = AsyncMock(return_value=mock_response)

            # Primera llamada — cache miss, va a AppSheet
            result1 = await client.find_patient_by_phone("1112345678")
            assert result1 == {"Paciente": "Test"}
            mock_redis.setex.assert_called_once()

            # Simular cache hit en segunda llamada
            mock_redis.get = AsyncMock(return_value=json.dumps({"Paciente": "Test"}))
            result2 = await client.find_patient_by_phone("1112345678")
            assert result2 == {"Paciente": "Test"}

    async def test_caches_not_found_as_false(self, client, mock_redis):
        """Paciente no encontrado → cachea False para evitar re-búsqueda."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "[]"
            mock_response.json.return_value = []
            client._client.post = AsyncMock(return_value=mock_response)

            result = await client.find_patient_by_phone("0000000000")
            assert result is None

            # Verificar que cacheó False
            call_args = mock_redis.setex.call_args
            assert json.loads(call_args[0][2]) is False

    async def test_returns_none_for_cached_false(self, client, mock_redis):
        """Cache con False → retorna None (no encontrado cacheado)."""
        mock_redis.get = AsyncMock(return_value=json.dumps(False))
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await client.find_patient_by_phone("0000000000")
            assert result is None
            # No debería haber llamado a AppSheet
            client._client.post.assert_not_called()


class TestLeadCache:
    async def test_cache_hit(self, client, mock_redis):
        """Lead cacheado → retorna sin llamar AppSheet."""
        mock_redis.get = AsyncMock(return_value=json.dumps({"Apellido y Nombre": "Test Lead"}))
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await client.find_lead_by_phone("1199887766")
            assert result == {"Apellido y Nombre": "Test Lead"}
            client._client.post.assert_not_called()


# =============================================================================
# CACHE TABLAS ESTÁTICAS
# =============================================================================

class TestStaticTableCache:
    async def test_horarios_cached_24h(self, client, mock_redis):
        """Horarios de atención se cachean con TTL 24h."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '[{"DIA": "LUNES"}]'
            mock_response.json.return_value = [{"DIA": "LUNES"}]
            client._client.post = AsyncMock(return_value=mock_response)

            result = await client.find("LISTA O | HORARIOS DE ATENCION")
            assert result == [{"DIA": "LUNES"}]

            # Verificar TTL de 24h (86400s)
            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 86400

    async def test_tarifario_cached_with_selector(self, client, mock_redis):
        """Tarifario con selector se cachea por selector."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '[{"Precio Lista": 15000}]'
            mock_response.json.return_value = [{"Precio Lista": 15000}]
            client._client.post = AsyncMock(return_value=mock_response)

            selector = 'Filter(BBDD TARIFARIO, [Tratamiento Detalle] = "Alineadores")'
            result = await client.find("BBDD TARIFARIO", selector=selector)
            assert result[0]["Precio Lista"] == 15000

            # Verificar key incluye selector
            cache_key = mock_redis.setex.call_args[0][0]
            assert "Alineadores" in cache_key

    async def test_static_cache_hit(self, client, mock_redis):
        """Cache hit para tabla estática → no llama AppSheet."""
        mock_redis.get = AsyncMock(
            return_value=json.dumps([{"DIA": "LUNES"}, {"DIA": "MARTES"}])
        )
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            result = await client.find("LISTA O | HORARIOS DE ATENCION")
            assert len(result) == 2
            client._client.post.assert_not_called()

    async def test_non_static_table_not_cached(self, client, mock_redis):
        """Tablas no estáticas (BBDD SESIONES) NO se cachean."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '[{"ID": "SES-1"}]'
            mock_response.json.return_value = [{"ID": "SES-1"}]
            client._client.post = AsyncMock(return_value=mock_response)

            await client.find("BBDD SESIONES", selector="Filter(...)")
            # No debería cachear BBDD SESIONES
            mock_redis.setex.assert_not_called()


# =============================================================================
# CACHE INVALIDATION
# =============================================================================

class TestCacheInvalidation:
    async def test_add_patient_invalidates_cache(self, client, mock_redis):
        """Crear paciente → invalida cache por teléfono."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '[{"Paciente": "New"}]'
            mock_response.json.return_value = [{"Paciente": "New"}]
            client._client.post = AsyncMock(return_value=mock_response)

            await client.add("BBDD PACIENTES", [{"Telefono (Whatsapp)": "5491112345678"}])
            mock_redis.delete.assert_called_once_with("cache:patient:1112345678")

    async def test_add_lead_invalidates_cache(self, client, mock_redis):
        """Crear lead → invalida cache de lead."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '[{"Lead": "New"}]'
            mock_response.json.return_value = [{"Lead": "New"}]
            client._client.post = AsyncMock(return_value=mock_response)

            await client.add("BBDD LEADS", [{"Telefono (Whatsapp)": "5491199887766"}])
            mock_redis.delete.assert_called_once_with("cache:lead:1199887766")


# =============================================================================
# GRACEFUL DEGRADATION (Redis caído)
# =============================================================================

class TestGracefulDegradation:
    async def test_works_without_redis(self, client):
        """Sin Redis → funciona normalmente (sin cache)."""
        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=None):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '[{"Paciente": "Test"}]'
            mock_response.json.return_value = [{"Paciente": "Test"}]
            client._client.post = AsyncMock(return_value=mock_response)

            result = await client.find_patient_by_phone("1112345678")
            assert result == {"Paciente": "Test"}

    async def test_redis_error_falls_through(self, client):
        """Error de Redis → sigue sin cache, no crashea."""
        mock_redis_broken = AsyncMock()
        mock_redis_broken.get = AsyncMock(side_effect=Exception("Redis down"))
        mock_redis_broken.setex = AsyncMock(side_effect=Exception("Redis down"))

        with patch("src.clients.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis_broken):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '[{"Paciente": "Test"}]'
            mock_response.json.return_value = [{"Paciente": "Test"}]
            client._client.post = AsyncMock(return_value=mock_response)

            result = await client.find_patient_by_phone("1112345678")
            assert result == {"Paciente": "Test"}

"""
Tests del cliente WhatsApp — retry con backoff en send_text.
Verifica retry en errores de red, no retry en errores de cliente, y éxito tras reintentos.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.whatsapp import send_text


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings para todos los tests."""
    with patch("src.clients.whatsapp.get_settings") as mock:
        mock.return_value = MagicMock(
            whatsapp_token="test-token",
            whatsapp_phone_number_id="123456",
            whatsapp_max_retries=3,
        )
        yield mock


@pytest.fixture
def mock_send():
    """Mock de _send_message."""
    with patch("src.clients.whatsapp._send_message", new_callable=AsyncMock) as mock:
        yield mock


class TestSendTextRetry:
    async def test_success_no_retry(self, mock_send):
        """Éxito en primer intento → sin retry."""
        mock_send.return_value = {"status": "ok", "wa_message_id": "wamid.001"}

        result = await send_text("549111234567", "Hola!")

        assert result["status"] == "ok"
        assert mock_send.call_count == 1

    async def test_success_on_second_attempt(self, mock_send):
        """Falla en primer intento, éxito en segundo."""
        mock_send.side_effect = [
            {"status": "error", "error": "Timeout al enviar mensaje"},
            {"status": "ok", "wa_message_id": "wamid.002"},
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await send_text("549111234567", "Hola!")

        assert result["status"] == "ok"
        assert mock_send.call_count == 2

    async def test_all_retries_fail(self, mock_send):
        """Todos los reintentos fallan → retorna último error."""
        mock_send.return_value = {"status": "error", "error": "Connection refused"}

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await send_text("549111234567", "Hola!")

        assert result["status"] == "error"
        assert mock_send.call_count == 3  # 3 intentos (max_retries)

    async def test_no_retry_on_400_error(self, mock_send):
        """Error 400 (client error) → NO reintentar."""
        mock_send.return_value = {
            "status": "error",
            "error": {"code": 400, "message": "Invalid phone number"},
        }

        result = await send_text("invalid", "Hola!")

        assert result["status"] == "error"
        assert mock_send.call_count == 1  # Solo 1 intento

    async def test_no_retry_on_401_error(self, mock_send):
        """Error 401 (auth error) → NO reintentar."""
        mock_send.return_value = {
            "status": "error",
            "error": {"code": 401, "message": "Invalid token"},
        }

        result = await send_text("549111234567", "Hola!")

        assert result["status"] == "error"
        assert mock_send.call_count == 1

    async def test_retry_on_500_error(self, mock_send):
        """Error 500 (server error) → SÍ reintentar."""
        mock_send.side_effect = [
            {"status": "error", "error": {"code": 500, "message": "Internal error"}},
            {"status": "ok", "wa_message_id": "wamid.003"},
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await send_text("549111234567", "Hola!")

        assert result["status"] == "ok"
        assert mock_send.call_count == 2

    async def test_retry_on_string_error(self, mock_send):
        """Error como string (timeout, connection) → SÍ reintentar."""
        mock_send.side_effect = [
            {"status": "error", "error": "Timeout al enviar mensaje"},
            {"status": "error", "error": "Connection reset"},
            {"status": "ok", "wa_message_id": "wamid.004"},
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await send_text("549111234567", "Hola!")

        assert result["status"] == "ok"
        assert mock_send.call_count == 3

    async def test_backoff_wait_times(self, mock_send):
        """Verifica que el backoff sea 2s, 4s (exponencial)."""
        mock_send.return_value = {"status": "error", "error": "Network error"}

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await send_text("549111234567", "Hola!")

        # 3 intentos → 2 sleeps (entre intentos 1→2 y 2→3)
        assert mock_sleep.call_count == 2
        # Backoff: 2^1=2, 2^2=4
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    async def test_payload_structure(self, mock_send):
        """Verifica que el payload de WhatsApp sea correcto."""
        mock_send.return_value = {"status": "ok", "wa_message_id": "wamid.005"}

        await send_text("5491112345678", "Hola paciente!")

        call_args = mock_send.call_args[0][0]
        assert call_args["messaging_product"] == "whatsapp"
        assert call_args["to"] == "5491112345678"
        assert call_args["type"] == "text"
        assert call_args["text"]["body"] == "Hola paciente!"

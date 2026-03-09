"""
Tests del cliente de transcripción de audio — Groq Whisper API.
Verifica transcripción exitosa, errores de API, timeout, audio vacío, y degradación graceful.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.clients.audio_transcription import (
    close_client,
    is_transcription_available,
    transcribe_audio,
)


FAKE_AUDIO = b"\x00\x01\x02\x03" * 100  # 400 bytes de audio falso


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings con GROQ_API_KEY configurada."""
    with patch("src.clients.audio_transcription.get_settings") as mock:
        mock.return_value = MagicMock(groq_api_key="test-groq-key")
        yield mock


@pytest.fixture(autouse=True)
def reset_client():
    """Reset del cliente HTTP entre tests."""
    import src.clients.audio_transcription as mod
    mod._http_client = None
    yield
    mod._http_client = None


@pytest.fixture
def mock_httpx():
    """Mock del cliente httpx para interceptar requests a Groq."""
    with patch("src.clients.audio_transcription._get_client") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


# =============================================================================
# Tests: is_transcription_available
# =============================================================================

class TestIsTranscriptionAvailable:
    def test_available_with_key(self, mock_settings):
        """Con API key configurada → True."""
        assert is_transcription_available() is True

    def test_not_available_without_key(self, mock_settings):
        """Sin API key → False."""
        mock_settings.return_value = MagicMock(groq_api_key="")
        assert is_transcription_available() is False

    def test_not_available_with_none_key(self, mock_settings):
        """API key None → False (bool(None) = False)."""
        mock_settings.return_value = MagicMock(groq_api_key=None)
        assert is_transcription_available() is False


# =============================================================================
# Tests: transcribe_audio
# =============================================================================

class TestTranscribeAudio:
    async def test_success(self, mock_httpx):
        """Transcripción exitosa → retorna texto."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Hola, quiero sacar un turno"}
        mock_httpx.post = AsyncMock(return_value=mock_response)

        result = await transcribe_audio(FAKE_AUDIO)

        assert result == "Hola, quiero sacar un turno"
        mock_httpx.post.assert_called_once()

        # Verificar que se envió como multipart con model y language
        call_kwargs = mock_httpx.post.call_args[1]
        assert "files" in call_kwargs
        assert call_kwargs["data"]["model"] == "whisper-large-v3-turbo"
        assert call_kwargs["data"]["language"] == "es"

    async def test_api_error_returns_none(self, mock_httpx):
        """Error de API (500) → None."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_httpx.post = AsyncMock(return_value=mock_response)

        result = await transcribe_audio(FAKE_AUDIO)
        assert result is None

    async def test_api_error_401_returns_none(self, mock_httpx):
        """Error 401 (API key inválida) → None."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API Key"
        mock_httpx.post = AsyncMock(return_value=mock_response)

        result = await transcribe_audio(FAKE_AUDIO)
        assert result is None

    async def test_empty_transcription_returns_none(self, mock_httpx):
        """Transcripción vacía → None (audio silencioso o ininteligible)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": ""}
        mock_httpx.post = AsyncMock(return_value=mock_response)

        result = await transcribe_audio(FAKE_AUDIO)
        assert result is None

    async def test_whitespace_transcription_returns_none(self, mock_httpx):
        """Transcripción solo espacios → None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "   \n  "}
        mock_httpx.post = AsyncMock(return_value=mock_response)

        result = await transcribe_audio(FAKE_AUDIO)
        assert result is None

    async def test_timeout_returns_none(self, mock_httpx):
        """Timeout de red → None."""
        mock_httpx.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        result = await transcribe_audio(FAKE_AUDIO)
        assert result is None

    async def test_network_error_returns_none(self, mock_httpx):
        """Error de red genérico → None."""
        mock_httpx.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        result = await transcribe_audio(FAKE_AUDIO)
        assert result is None

    async def test_no_api_key_returns_none(self, mock_settings):
        """Sin API key → None (sin llamar a Groq)."""
        mock_settings.return_value = MagicMock(groq_api_key="")

        result = await transcribe_audio(FAKE_AUDIO)
        assert result is None

    async def test_empty_audio_bytes_returns_none(self, mock_httpx):
        """Audio vacío (0 bytes) → None."""
        result = await transcribe_audio(b"")
        assert result is None
        mock_httpx.post.assert_not_called()

    async def test_custom_language(self, mock_httpx):
        """Se puede cambiar el idioma (ej: portugués)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Olá, tudo bem?"}
        mock_httpx.post = AsyncMock(return_value=mock_response)

        result = await transcribe_audio(FAKE_AUDIO, language="pt")

        assert result == "Olá, tudo bem?"
        call_kwargs = mock_httpx.post.call_args[1]
        assert call_kwargs["data"]["language"] == "pt"

    async def test_custom_model(self, mock_httpx):
        """Se puede cambiar el modelo."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Test"}
        mock_httpx.post = AsyncMock(return_value=mock_response)

        result = await transcribe_audio(FAKE_AUDIO, model="whisper-large-v3")

        assert result == "Test"
        call_kwargs = mock_httpx.post.call_args[1]
        assert call_kwargs["data"]["model"] == "whisper-large-v3"

    async def test_custom_filename(self, mock_httpx):
        """Se puede cambiar el filename (extensión importa para Groq)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Audio test"}
        mock_httpx.post = AsyncMock(return_value=mock_response)

        result = await transcribe_audio(FAKE_AUDIO, filename="recording.mp3")

        assert result == "Audio test"
        call_kwargs = mock_httpx.post.call_args[1]
        # El filename debe estar en los files
        file_tuple = call_kwargs["files"]["file"]
        assert file_tuple[0] == "recording.mp3"


# =============================================================================
# Tests: close_client
# =============================================================================

class TestCloseClient:
    async def test_close_client(self):
        """close_client cierra el httpx client."""
        import src.clients.audio_transcription as mod

        mock_client = AsyncMock()
        mock_client.is_closed = False
        mod._http_client = mock_client

        await close_client()

        mock_client.aclose.assert_called_once()
        assert mod._http_client is None

    async def test_close_client_when_none(self):
        """close_client con client None → no crashea."""
        import src.clients.audio_transcription as mod
        mod._http_client = None
        await close_client()  # No debe tirar error

"""
Cliente de transcripción de audio — Groq Whisper API.

Usa whisper-large-v3-turbo en Groq (ultra rápido, ~10x más rápido que OpenAI).
WhatsApp envía audio como .ogg (Opus) → Groq lo acepta directamente.

Endpoint: https://api.groq.com/openai/v1/audio/transcriptions
"""

from __future__ import annotations

from typing import Optional

import httpx

from src.config import get_settings
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_MODEL = "whisper-large-v3-turbo"

# Cliente HTTP reutilizable (lazy init)
_http_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    """Obtiene o crea el cliente HTTP con auth de Groq."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        settings = get_settings()
        _http_client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
            },
            timeout=30.0,
        )
    return _http_client


def is_transcription_available() -> bool:
    """Chequea si la transcripción de audio está disponible (API key configurada)."""
    settings = get_settings()
    return bool(settings.groq_api_key)


async def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.ogg",
    language: str = "es",
    model: str = DEFAULT_MODEL,
) -> Optional[str]:
    """
    Transcribe audio a texto usando Groq Whisper API.

    Args:
        audio_bytes: Bytes del archivo de audio
        filename: Nombre del archivo (con extensión para que Groq detecte formato)
        language: Código de idioma ISO 639-1 (default: "es" para español)
        model: Modelo Whisper a usar

    Returns:
        Texto transcrito o None si falla.
    """
    if not is_transcription_available():
        logger.warning("groq_api_key_not_configured")
        return None

    if not audio_bytes:
        logger.warning("transcribe_empty_audio")
        return None

    client = _get_client()

    try:
        response = await client.post(
            GROQ_API_URL,
            files={
                "file": (filename, audio_bytes, "audio/ogg"),
            },
            data={
                "model": model,
                "language": language,
            },
        )

        if response.status_code != 200:
            logger.error(
                "groq_transcription_error",
                status=response.status_code,
                error=response.text[:500],
            )
            return None

        data = response.json()
        text = data.get("text", "").strip()

        if not text:
            logger.warning("groq_transcription_empty")
            return None

        logger.info(
            "groq_transcription_ok",
            text_length=len(text),
            model=model,
            language=language,
        )
        return text

    except httpx.TimeoutException:
        logger.error("groq_transcription_timeout")
        return None
    except Exception as e:
        logger.error("groq_transcription_error", error=str(e))
        return None


async def close_client() -> None:
    """Cerrar el cliente HTTP (llamar en shutdown)."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None

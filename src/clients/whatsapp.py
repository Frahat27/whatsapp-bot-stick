"""
Cliente WhatsApp Cloud API v21.0.

Funciones:
- send_text: enviar mensaje de texto
- send_image: enviar imagen (por URL)
- send_document: enviar documento/PDF (por URL o media_id)
- send_template: enviar template message (recordatorios)
- download_media: descargar media recibida (para Vision / comprobantes)
- mark_as_read: marcar mensaje como leído (doble tilde azul)
"""

from typing import Optional

import httpx

from src.config import get_settings
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

WA_API_URL = "https://graph.facebook.com/v21.0"

# Cliente HTTP reutilizable (se inicializa lazy)
_http_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    """Obtiene o crea el cliente HTTP con headers de auth."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        settings = get_settings()
        _http_client = httpx.AsyncClient(
            base_url=WA_API_URL,
            headers={
                "Authorization": f"Bearer {settings.whatsapp_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    return _http_client


async def _send_message(payload: dict) -> dict:
    """
    Envía un mensaje genérico a la API de WhatsApp.
    Maneja errores y logging centralizados.
    """
    settings = get_settings()
    client = _get_client()
    url = f"/{settings.whatsapp_phone_number_id}/messages"

    try:
        response = await client.post(url, json=payload)
        data = response.json()

        if response.status_code != 200:
            logger.error(
                "whatsapp_send_error",
                status=response.status_code,
                error=data.get("error", {}),
                to=payload.get("to", ""),
            )
            return {"status": "error", "error": data}

        message_id = data.get("messages", [{}])[0].get("id", "")
        logger.info(
            "whatsapp_message_sent",
            to=payload.get("to", ""),
            type=payload.get("type", ""),
            wa_message_id=message_id,
        )
        return {"status": "ok", "wa_message_id": message_id, "data": data}

    except httpx.TimeoutException:
        logger.error("whatsapp_timeout", to=payload.get("to", ""))
        return {"status": "error", "error": "Timeout al enviar mensaje"}
    except Exception as e:
        logger.error("whatsapp_error", error=str(e), to=payload.get("to", ""))
        return {"status": "error", "error": str(e)}


async def send_text(to: str, text: str) -> dict:
    """
    Enviar mensaje de texto por WhatsApp.

    Args:
        to: Número destino en formato 549XXXXXXXXXX (sin +)
        text: Texto del mensaje (máx ~4096 chars)
    """
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    return await _send_message(payload)


async def send_image(
    to: str,
    image_url: str,
    caption: Optional[str] = None,
) -> dict:
    """
    Enviar imagen por URL.

    Args:
        to: Número destino
        image_url: URL pública de la imagen
        caption: Texto opcional debajo de la imagen
    """
    image_obj: dict = {"link": image_url}
    if caption:
        image_obj["caption"] = caption

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "image",
        "image": image_obj,
    }
    return await _send_message(payload)


async def send_document(
    to: str,
    document_url: Optional[str] = None,
    media_id: Optional[str] = None,
    filename: str = "documento.pdf",
    caption: Optional[str] = None,
) -> dict:
    """
    Enviar documento (PDF, etc.) por URL o media_id.

    Args:
        to: Número destino
        document_url: URL pública del documento
        media_id: ID de media previamente subido a WhatsApp
        filename: Nombre del archivo que verá el usuario
        caption: Texto opcional
    """
    doc_obj: dict = {"filename": filename}
    if media_id:
        doc_obj["id"] = media_id
    elif document_url:
        doc_obj["link"] = document_url
    else:
        return {"status": "error", "error": "Falta document_url o media_id"}

    if caption:
        doc_obj["caption"] = caption

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "document",
        "document": doc_obj,
    }
    return await _send_message(payload)


async def send_template(
    to: str,
    template_name: str,
    language: str = "es_AR",
    parameters: Optional[list[str]] = None,
) -> dict:
    """
    Enviar template message (para recordatorios, bienvenida, etc.).

    Args:
        to: Número destino
        template_name: Nombre del template aprobado en Meta
        language: Código de idioma (default: es_AR)
        parameters: Lista de valores para los parámetros {{1}}, {{2}}, etc.
    """
    template_obj: dict = {
        "name": template_name,
        "language": {"code": language},
    }

    if parameters:
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": p} for p in parameters
                ],
            }
        ]
        template_obj["components"] = components

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "template",
        "template": template_obj,
    }
    return await _send_message(payload)


async def mark_as_read(message_id: str) -> dict:
    """
    Marcar un mensaje como leído (doble tilde azul).

    Args:
        message_id: ID del mensaje de WhatsApp (wamid.xxx)
    """
    settings = get_settings()
    client = _get_client()
    url = f"/{settings.whatsapp_phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    try:
        response = await client.post(url, json=payload)
        if response.status_code == 200:
            logger.debug("whatsapp_marked_read", message_id=message_id)
            return {"status": "ok"}
        return {"status": "error", "error": response.json()}
    except Exception as e:
        logger.error("whatsapp_mark_read_error", error=str(e))
        return {"status": "error", "error": str(e)}


async def download_media(media_id: str) -> Optional[bytes]:
    """
    Descargar archivo de media de WhatsApp (comprobantes, imágenes).

    Proceso de 2 pasos:
    1. GET /{media_id} → obtiene la URL temporal de descarga
    2. GET url → descarga el archivo binario

    Args:
        media_id: ID del media recibido en el webhook

    Returns:
        Bytes del archivo o None si falla.
    """
    settings = get_settings()
    client = _get_client()

    try:
        # Paso 1: obtener URL de descarga
        response = await client.get(f"/{media_id}")
        if response.status_code != 200:
            logger.error("whatsapp_media_url_error", media_id=media_id)
            return None

        media_url = response.json().get("url")
        if not media_url:
            logger.error("whatsapp_media_no_url", media_id=media_id)
            return None

        # Paso 2: descargar el archivo (URL temporal requiere auth)
        download_response = await client.get(
            media_url,
            headers={
                "Authorization": f"Bearer {settings.whatsapp_token}",
            },
        )

        if download_response.status_code != 200:
            logger.error(
                "whatsapp_media_download_error",
                media_id=media_id,
                status=download_response.status_code,
            )
            return None

        logger.info(
            "whatsapp_media_downloaded",
            media_id=media_id,
            size=len(download_response.content),
        )
        return download_response.content

    except Exception as e:
        logger.error("whatsapp_media_error", error=str(e), media_id=media_id)
        return None


async def close_client():
    """Cerrar el cliente HTTP (llamar en shutdown)."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None

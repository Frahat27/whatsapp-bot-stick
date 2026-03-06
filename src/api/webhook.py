"""
Endpoints del webhook de WhatsApp Business API.

GET  /webhook → Verificación de Meta (hub.verify_token)
POST /webhook → Recepción de mensajes entrantes
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db.session import get_db
from src.schemas.webhook import WhatsAppWebhookPayload
from src.utils.logging_config import get_logger
from src.utils.phone import normalize_phone

router = APIRouter()
logger = get_logger(__name__)


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Verificación del webhook por Meta.
    Meta envía un GET con hub.mode, hub.verify_token, hub.challenge.
    Si el token coincide, se devuelve hub.challenge.
    """
    settings = get_settings()

    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("webhook_verified")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning("webhook_verification_failed", mode=hub_mode)
    return Response(content="Forbidden", status_code=403)


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
):
    """
    Recibe mensajes de WhatsApp.

    Flujo:
    1. Validar firma del webhook (X-Hub-Signature-256)
    2. Parsear payload
    3. Responder 200 inmediatamente (requerimiento de Meta)
    4. Procesar mensaje en background
    """
    settings = get_settings()

    # 1. Leer body raw para validar firma
    body = await request.body()

    # 2. Validar firma si hay app_secret configurado
    if settings.whatsapp_app_secret and x_hub_signature_256:
        if not _verify_signature(body, settings.whatsapp_app_secret, x_hub_signature_256):
            logger.warning("webhook_invalid_signature")
            return Response(content="Invalid signature", status_code=403)

    # 3. Parsear payload
    try:
        payload_data = await request.json()
        payload = WhatsAppWebhookPayload.model_validate(payload_data)
    except Exception as e:
        logger.error("webhook_parse_error", error=str(e))
        return {"status": "ok"}  # Siempre 200 para Meta

    # 4. Extraer mensajes
    messages = payload.get_messages()
    contact_name = payload.get_contact_name()

    if not messages:
        # Puede ser un status update (delivered, read, etc.)
        logger.debug("webhook_no_messages", payload_type="status_update")
        return {"status": "ok"}

    # 5. Procesar cada mensaje en background
    for msg in messages:
        phone = normalize_phone(msg.from_)
        content = _extract_content(msg)
        media_id = _extract_media_id(msg)
        logger.info(
            "webhook_message_received",
            phone=phone,
            type=msg.type,
            wa_id=msg.id,
            contact_name=contact_name,
        )

        background_tasks.add_task(
            _process_message,
            phone=phone,
            content=content,
            message_type=msg.type,
            wa_message_id=msg.id,
            contact_name=contact_name,
            media_id=media_id,
        )

    return {"status": "ok"}


def _verify_signature(body: bytes, app_secret: str, signature_header: str) -> bool:
    """Verifica la firma HMAC-SHA256 del webhook."""
    expected = hmac.new(
        app_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header.replace("sha256=", "")
    return hmac.compare_digest(expected, received)


def _extract_content(msg) -> str:
    """Extrae el contenido de texto de un mensaje de WhatsApp."""
    if msg.type == "text" and msg.text:
        return msg.text.body
    elif msg.type == "image" and msg.image:
        return msg.image.caption or "[Imagen recibida]"
    elif msg.type == "audio":
        return "[Audio recibido]"
    elif msg.type == "document" and msg.document:
        return msg.document.caption or f"[Documento: {msg.document.filename or 'sin nombre'}]"
    elif msg.type == "location" and msg.location:
        return f"[Ubicación: {msg.location.latitude}, {msg.location.longitude}]"
    elif msg.type == "sticker":
        return "[Sticker recibido]"
    elif msg.type == "reaction":
        return "[Reacción]"
    return f"[Mensaje tipo: {msg.type}]"


def _extract_media_id(msg) -> str | None:
    """Extrae el media_id de mensajes con contenido multimedia."""
    if msg.type == "image" and msg.image:
        return msg.image.id
    elif msg.type == "audio" and msg.audio:
        return msg.audio.id
    elif msg.type == "document" and msg.document:
        return msg.document.id
    return None


async def _process_message(
    phone: str,
    content: str,
    message_type: str,
    wa_message_id: str,
    contact_name: str | None,
    media_id: str | None = None,
) -> None:
    """
    Procesa un mensaje entrante usando ConversationManager.
    Se ejecuta como background task (fuera del request HTTP).
    Crea su propia DB session ya que el request original ya cerró la suya.
    """
    from src.db.session import get_session_factory
    from src.services.conversation_manager import ConversationManager

    factory = get_session_factory()
    async with factory() as db:
        try:
            manager = ConversationManager(db)
            await manager.handle_incoming_message(
                phone=phone,
                content=content,
                message_type=message_type,
                wa_message_id=wa_message_id,
                contact_name=contact_name,
                media_id=media_id,
            )
        except Exception as e:
            logger.error(
                "message_processing_error",
                phone=phone,
                error=str(e),
                wa_id=wa_message_id,
            )
            await db.rollback()

"""
Helper para enviar mensajes proactivos (iniciados por el bot).

Usado por el sistema de recordatorios para:
1. Buscar o crear una conversacion para el numero de telefono
2. Guardar el mensaje saliente como role=ASSISTANT en la DB
3. Enviar via WhatsApp (texto)

Esto asegura que Claude vea el recordatorio en el historial
cuando el paciente responda.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.whatsapp import send_text
from src.models.conversation import Conversation, ContactType
from src.models.conversation_state import ConversationState, ConversationStatus
from src.models.message import Message, MessageRole, MessageType
from src.utils.logging_config import get_logger
from src.utils.phone import to_whatsapp_format

logger = get_logger(__name__)


async def send_proactive_message(
    db: AsyncSession,
    phone_10: str,
    text: str,
    patient_name: Optional[str] = None,
    patient_id: Optional[str] = None,
    contact_type: ContactType = ContactType.PACIENTE,
) -> dict:
    """
    Enviar un mensaje proactivo y guardarlo en el historial.

    Args:
        db: Sesion async de DB
        phone_10: Telefono normalizado a 10 digitos
        text: Texto del mensaje a enviar
        patient_name: Nombre opcional (para creacion de conversacion)
        patient_id: ID AppSheet opcional del paciente
        contact_type: Tipo de contacto (PACIENTE, LEAD, etc.)

    Returns:
        dict con "status" key ("ok" o "error") y opcional "wa_message_id"
    """
    # 1. Buscar o crear conversacion
    conversation = await _get_or_create_conversation(
        db, phone_10, patient_name, patient_id, contact_type,
    )

    # 2. Guardar como mensaje ASSISTANT (para que Claude lo vea en el historial)
    message = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=text,
        message_type=MessageType.TEXT,
    )
    db.add(message)
    await db.flush()

    # 3. Enviar via WhatsApp
    wa_phone = to_whatsapp_format(phone_10)
    result = await send_text(to=wa_phone, text=text)

    if result.get("status") == "ok":
        logger.info(
            "proactive_message_sent",
            phone=phone_10,
            wa_message_id=result.get("wa_message_id"),
            text_preview=text[:60],
        )
    else:
        logger.error(
            "proactive_message_failed",
            phone=phone_10,
            error=str(result.get("error", ""))[:200],
        )

    return result


async def _get_or_create_conversation(
    db: AsyncSession,
    phone_10: str,
    patient_name: Optional[str],
    patient_id: Optional[str],
    contact_type: ContactType,
) -> Conversation:
    """Buscar conversacion existente o crear una nueva."""
    stmt = select(Conversation).where(Conversation.phone == phone_10)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if conversation is None:
        conversation = Conversation(
            phone=phone_10,
            contact_type=contact_type,
            patient_id=patient_id,
            patient_name=patient_name,
        )
        db.add(conversation)

        state = ConversationState(
            conversation=conversation,
            status=ConversationStatus.BOT_ACTIVE,
        )
        db.add(state)

        await db.flush()
        logger.info("proactive_conversation_created", phone=phone_10)

    return conversation

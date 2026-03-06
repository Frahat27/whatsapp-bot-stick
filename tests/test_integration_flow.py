"""
Tests de integración — flujo completo de mensaje.

Simula: webhook → ConversationManager → Claude → tools → DB → WhatsApp

Mocks:
- WhatsApp client (no enviar mensajes reales)
- Claude AI (respuestas predecibles)
- AppSheet (evitar rate limiting)

Real:
- PostgreSQL (Neon) con rollback por test
"""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from sqlalchemy import select

from src.models.conversation import Conversation, ContactType
from src.models.message import Message, MessageRole
from src.models.conversation_state import ConversationState, ConversationStatus
from src.services.conversation_manager import ConversationManager, _ensure_alternation


# =============================================================================
# HELPER: Patch todas las dependencias externas
# =============================================================================

def _external_mocks():
    """Context manager que mockea WhatsApp, Claude y AppSheet."""
    return (
        patch("src.services.conversation_manager.send_text", new_callable=AsyncMock),
        patch("src.services.conversation_manager.mark_as_read", new_callable=AsyncMock),
        patch("src.services.conversation_manager.generate_response", new_callable=AsyncMock),
        patch("src.services.conversation_manager.get_appsheet_client"),
    )


# =============================================================================
# TESTS DE FLUJO COMPLETO
# =============================================================================

class TestNewContactFlow:
    """Contacto nuevo envía mensaje por primera vez."""

    async def test_creates_conversation_and_responds(self, db_session):
        mock_send, mock_read, mock_claude, mock_appsheet_factory = (
            AsyncMock(), AsyncMock(), AsyncMock(), MagicMock()
        )
        mock_claude.return_value = "¡Hola! Soy Sofia de STICK 😊 ¿En qué puedo ayudarte?"

        # AppSheet: no encuentra paciente ni lead
        mock_appsheet = MagicMock()
        mock_appsheet.find_patient_by_phone = AsyncMock(return_value=None)
        mock_appsheet.find_lead_by_phone = AsyncMock(return_value=None)
        mock_appsheet_factory.return_value = mock_appsheet

        with patch("src.services.conversation_manager.send_text", mock_send), \
             patch("src.services.conversation_manager.mark_as_read", mock_read), \
             patch("src.services.conversation_manager.generate_response", mock_claude), \
             patch("src.services.conversation_manager.get_appsheet_client", mock_appsheet_factory):

            manager = ConversationManager(db_session)
            result = await manager.handle_incoming_message(
                phone="1199887766",
                content="Hola buenas tardes",
                message_type="text",
                wa_message_id="wamid.test_new_001",
                contact_name="Test User",
            )

        # Verifica respuesta
        assert result is not None
        assert "Sofia" in result or "STICK" in result

        # Verifica conversación en DB
        stmt = select(Conversation).where(Conversation.phone == "1199887766")
        conv = (await db_session.execute(stmt)).scalar_one_or_none()
        assert conv is not None
        assert conv.contact_type == ContactType.NUEVO

        # Verifica que se guardaron 2 mensajes (user + assistant)
        stmt_msgs = select(Message).where(
            Message.conversation_id == conv.id
        ).order_by(Message.created_at)
        msgs = (await db_session.execute(stmt_msgs)).scalars().all()
        assert len(msgs) == 2
        assert msgs[0].role == MessageRole.USER
        assert msgs[0].content == "Hola buenas tardes"
        assert msgs[1].role == MessageRole.ASSISTANT

        # Verifica que se llamó a WhatsApp
        mock_send.assert_called_once()
        mock_read.assert_called_once_with("wamid.test_new_001")


class TestDuplicateMessage:
    """Mensaje duplicado (mismo wa_message_id) se rechaza."""

    async def test_dedup_rejects_second_message(self, db_session):
        mock_send = AsyncMock()
        mock_read = AsyncMock()
        mock_claude = AsyncMock(return_value="Respuesta")
        mock_appsheet = MagicMock()
        mock_appsheet.find_patient_by_phone = AsyncMock(return_value=None)
        mock_appsheet.find_lead_by_phone = AsyncMock(return_value=None)
        mock_appsheet_factory = MagicMock(return_value=mock_appsheet)

        with patch("src.services.conversation_manager.send_text", mock_send), \
             patch("src.services.conversation_manager.mark_as_read", mock_read), \
             patch("src.services.conversation_manager.generate_response", mock_claude), \
             patch("src.services.conversation_manager.get_appsheet_client", mock_appsheet_factory):

            manager = ConversationManager(db_session)

            # Primer mensaje
            result1 = await manager.handle_incoming_message(
                phone="1188776655",
                content="Hola",
                wa_message_id="wamid.dedup_test_001",
            )
            assert result1 is not None

            # Segundo mensaje con mismo wa_message_id
            result2 = await manager.handle_incoming_message(
                phone="1188776655",
                content="Hola de nuevo",
                wa_message_id="wamid.dedup_test_001",
            )
            assert result2 is None  # Rechazado

            # Claude se llamó solo 1 vez
            assert mock_claude.call_count == 1


class TestEscalatedConversation:
    """Conversación escalada — bot no responde."""

    async def test_bot_silent_when_escalated(self, db_session):
        mock_claude = AsyncMock(return_value="No debería llegar")

        # Crear conversación escalada manualmente
        conv = Conversation(phone="1177665544", contact_type=ContactType.PACIENTE)
        db_session.add(conv)
        await db_session.flush()

        state = ConversationState(
            conversation_id=conv.id,
            status=ConversationStatus.ESCALATED,
        )
        db_session.add(state)
        await db_session.flush()
        # Refresh para que conversation.state esté disponible
        await db_session.refresh(conv, attribute_names=["state", "messages"])

        mock_appsheet = MagicMock()
        mock_appsheet_factory = MagicMock(return_value=mock_appsheet)

        with patch("src.services.conversation_manager.send_text", AsyncMock()), \
             patch("src.services.conversation_manager.mark_as_read", AsyncMock()), \
             patch("src.services.conversation_manager.generate_response", mock_claude), \
             patch("src.services.conversation_manager.get_appsheet_client", mock_appsheet_factory):

            manager = ConversationManager(db_session)
            result = await manager.handle_incoming_message(
                phone="1177665544",
                content="Necesito ayuda urgente",
                wa_message_id="wamid.escalated_001",
            )

        assert result is None
        mock_claude.assert_not_called()


class TestAdminDetection:
    """Detección de admin por teléfono."""

    async def test_admin_phone_detected(self, db_session):
        mock_claude = AsyncMock(return_value="Hola Franco")
        mock_appsheet = MagicMock()
        mock_appsheet_factory = MagicMock(return_value=mock_appsheet)

        with patch("src.services.conversation_manager.send_text", AsyncMock()), \
             patch("src.services.conversation_manager.mark_as_read", AsyncMock()), \
             patch("src.services.conversation_manager.generate_response", mock_claude), \
             patch("src.services.conversation_manager.get_appsheet_client", mock_appsheet_factory):

            manager = ConversationManager(db_session)
            result = await manager.handle_incoming_message(
                phone="1123266671",  # Franco - admin
                content="Estado del bot",
                wa_message_id="wamid.admin_001",
            )

        assert result is not None

        # Verificar que la conversación se marcó como ADMIN
        stmt = select(Conversation).where(Conversation.phone == "1123266671")
        conv = (await db_session.execute(stmt)).scalar_one()
        assert conv.contact_type == ContactType.ADMIN

        # Verificar que Claude recibió contexto con es_admin y tipo_contacto
        call_kwargs = mock_claude.call_args[1]
        patient_ctx = call_kwargs.get("patient_context", {})
        assert patient_ctx.get("es_admin") is True
        assert patient_ctx.get("tipo_contacto") == "admin"


# =============================================================================
# TESTS DE HELPERS
# =============================================================================

class TestEnsureAlternation:
    def test_empty_list(self):
        assert _ensure_alternation([]) == []

    def test_single_message(self):
        msgs = [{"role": "user", "content": "Hola"}]
        assert _ensure_alternation(msgs) == msgs

    def test_already_alternating(self):
        msgs = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "Respuesta"},
        ]
        assert _ensure_alternation(msgs) == msgs

    def test_consecutive_user_messages_merged(self):
        msgs = [
            {"role": "user", "content": "Hola"},
            {"role": "user", "content": "¿Están?"},
            {"role": "assistant", "content": "Sí!"},
        ]
        result = _ensure_alternation(msgs)
        assert len(result) == 2
        assert "Hola" in result[0]["content"]
        assert "¿Están?" in result[0]["content"]

    def test_consecutive_assistant_messages_merged(self):
        msgs = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "Parte 1"},
            {"role": "assistant", "content": "Parte 2"},
        ]
        result = _ensure_alternation(msgs)
        assert len(result) == 2
        assert "Parte 1" in result[1]["content"]
        assert "Parte 2" in result[1]["content"]

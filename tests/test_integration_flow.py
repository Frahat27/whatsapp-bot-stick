"""
Tests de integracion — flujo completo de mensaje.

Simula: webhook -> ConversationManager -> Claude -> tools -> DB -> WhatsApp

Mocks:
- WhatsApp client (no enviar mensajes reales)
- Claude AI (respuestas predecibles)
- ClinicRepository (evitar acceso a Cloud SQL)

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


def _make_clinic_db():
    """Create an AsyncMock that acts as the clinic_db AsyncSession."""
    mock = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock


# =============================================================================
# TESTS DE FLUJO COMPLETO
# =============================================================================

class TestNewContactFlow:
    """Contacto nuevo envia mensaje por primera vez."""

    async def test_creates_conversation_and_responds(self, db_session):
        mock_send, mock_read, mock_claude = (
            AsyncMock(), AsyncMock(), AsyncMock()
        )
        mock_claude.return_value = "!Hola! Soy Sofia de STICK. En que puedo ayudarte?"
        mock_clinic_db = _make_clinic_db()

        with patch("src.services.conversation_manager.send_text", mock_send), \
             patch("src.services.conversation_manager.mark_as_read", mock_read), \
             patch("src.services.conversation_manager.generate_response", mock_claude):

            manager = ConversationManager(db_session, mock_clinic_db)
            # Mock clinic_repo methods: no patient, no lead -> NUEVO
            manager.clinic_repo.find_patient_by_phone = AsyncMock(return_value=None)
            manager.clinic_repo.find_lead_by_phone = AsyncMock(return_value=None)

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

        # Verifica conversacion en DB
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

        # Verifica que se llamo a WhatsApp
        mock_send.assert_called_once()
        mock_read.assert_called_once_with("wamid.test_new_001")


class TestDuplicateMessage:
    """Mensaje duplicado (mismo wa_message_id) se rechaza."""

    async def test_dedup_rejects_second_message(self, db_session):
        mock_send = AsyncMock()
        mock_read = AsyncMock()
        mock_claude = AsyncMock(return_value="Respuesta")
        mock_clinic_db = _make_clinic_db()

        with patch("src.services.conversation_manager.send_text", mock_send), \
             patch("src.services.conversation_manager.mark_as_read", mock_read), \
             patch("src.services.conversation_manager.generate_response", mock_claude):

            manager = ConversationManager(db_session, mock_clinic_db)
            manager.clinic_repo.find_patient_by_phone = AsyncMock(return_value=None)
            manager.clinic_repo.find_lead_by_phone = AsyncMock(return_value=None)

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

            # Claude se llamo solo 1 vez
            assert mock_claude.call_count == 1


class TestEscalatedConversation:
    """Conversacion escalada — bot no responde."""

    async def test_bot_silent_when_escalated(self, db_session):
        mock_claude = AsyncMock(return_value="No deberia llegar")
        mock_clinic_db = _make_clinic_db()

        # Crear conversacion escalada manualmente
        conv = Conversation(phone="1177665544", contact_type=ContactType.PACIENTE)
        db_session.add(conv)
        await db_session.flush()

        state = ConversationState(
            conversation_id=conv.id,
            status=ConversationStatus.ESCALATED,
        )
        db_session.add(state)
        await db_session.flush()
        # Refresh para que conversation.state este disponible
        await db_session.refresh(conv, attribute_names=["state", "messages"])

        with patch("src.services.conversation_manager.send_text", AsyncMock()), \
             patch("src.services.conversation_manager.mark_as_read", AsyncMock()), \
             patch("src.services.conversation_manager.generate_response", mock_claude):

            manager = ConversationManager(db_session, mock_clinic_db)
            result = await manager.handle_incoming_message(
                phone="1177665544",
                content="Necesito ayuda urgente",
                wa_message_id="wamid.escalated_001",
            )

        assert result is None
        mock_claude.assert_not_called()


class TestAdminDetection:
    """Deteccion de admin por telefono."""

    async def test_admin_phone_detected(self, db_session):
        mock_claude = AsyncMock(return_value="Hola Franco")
        mock_clinic_db = _make_clinic_db()

        with patch("src.services.conversation_manager.send_text", AsyncMock()), \
             patch("src.services.conversation_manager.mark_as_read", AsyncMock()), \
             patch("src.services.conversation_manager.generate_response", mock_claude):

            manager = ConversationManager(db_session, mock_clinic_db)
            # Admin is identified by phone, but _identify_contact still runs;
            # it short-circuits on the admin check before hitting clinic_repo.
            result = await manager.handle_incoming_message(
                phone="1123266671",  # Franco - admin
                content="Estado del bot",
                wa_message_id="wamid.admin_001",
            )

        assert result is not None

        # Verificar que la conversacion se marco como ADMIN
        stmt = select(Conversation).where(Conversation.phone == "1123266671")
        conv = (await db_session.execute(stmt)).scalar_one()
        assert conv.contact_type == ContactType.ADMIN

        # Verificar que Claude recibio contexto con es_admin y tipo_contacto
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
            {"role": "user", "content": "Estan?"},
            {"role": "assistant", "content": "Si!"},
        ]
        result = _ensure_alternation(msgs)
        assert len(result) == 2
        assert "Hola" in result[0]["content"]
        assert "Estan?" in result[0]["content"]

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


# =============================================================================
# TESTS DE AUDIO
# =============================================================================

class TestAudioMessage:
    """Audio transcrito -> Claude responde al contenido del audio."""

    async def test_audio_transcribed_and_claude_responds(self, db_session):
        """Audio -> transcripcion -> Claude responde con texto normal."""
        mock_send = AsyncMock()
        mock_read = AsyncMock()
        mock_claude = AsyncMock(return_value="Perfecto, te agendo un turno para el lunes.")
        mock_clinic_db = _make_clinic_db()

        with patch("src.services.conversation_manager.send_text", mock_send), \
             patch("src.services.conversation_manager.mark_as_read", mock_read), \
             patch("src.services.conversation_manager.generate_response", mock_claude), \
             patch("src.services.conversation_manager.download_media", AsyncMock(return_value=b"\x00\x01\x02")), \
             patch("src.clients.audio_transcription.get_settings", return_value=MagicMock(groq_api_key="test-key")), \
             patch("src.clients.audio_transcription._get_client") as mock_groq:

            # Mock Groq response
            groq_response = MagicMock()
            groq_response.status_code = 200
            groq_response.json.return_value = {"text": "Hola, quiero sacar un turno para el lunes"}
            mock_groq.return_value.post = AsyncMock(return_value=groq_response)

            manager = ConversationManager(db_session, mock_clinic_db)
            manager.clinic_repo.find_patient_by_phone = AsyncMock(return_value=None)
            manager.clinic_repo.find_lead_by_phone = AsyncMock(return_value=None)

            result = await manager.handle_incoming_message(
                phone="1199001122",
                content="[Audio recibido]",
                message_type="audio",
                wa_message_id="wamid.audio_001",
                media_id="media_audio_001",
            )

        assert result is not None
        assert "turno" in result.lower() or "lunes" in result.lower()

        # Verificar que Claude recibio el texto transcrito (no "[Audio recibido]")
        call_kwargs = mock_claude.call_args[1]
        messages_sent = call_kwargs["messages"]
        last_user_msg = [m for m in messages_sent if m["role"] == "user"][-1]
        assert "El paciente envi" in last_user_msg["content"]
        assert "quiero sacar un turno" in last_user_msg["content"]

    async def test_audio_without_groq_key_asks_for_text(self, db_session):
        """Sin GROQ_API_KEY -> pide escribir por texto."""
        mock_send = AsyncMock()
        mock_claude = AsyncMock(return_value="No deberia llegar")
        mock_clinic_db = _make_clinic_db()

        with patch("src.services.conversation_manager.send_text", mock_send), \
             patch("src.services.conversation_manager.mark_as_read", AsyncMock()), \
             patch("src.services.conversation_manager.generate_response", mock_claude), \
             patch("src.clients.audio_transcription.get_settings", return_value=MagicMock(groq_api_key="")):

            manager = ConversationManager(db_session, mock_clinic_db)
            manager.clinic_repo.find_patient_by_phone = AsyncMock(return_value=None)
            manager.clinic_repo.find_lead_by_phone = AsyncMock(return_value=None)

            result = await manager.handle_incoming_message(
                phone="1199002233",
                content="[Audio recibido]",
                message_type="audio",
                wa_message_id="wamid.audio_no_key",
                media_id="media_audio_no_key",
            )

        assert result is not None
        assert "texto" in result.lower()
        # Claude NO debe haber sido llamado
        mock_claude.assert_not_called()

    async def test_audio_download_fails_asks_resend(self, db_session):
        """Download de audio falla -> pide reenvio."""
        mock_send = AsyncMock()
        mock_claude = AsyncMock(return_value="No deberia llegar")
        mock_clinic_db = _make_clinic_db()

        with patch("src.services.conversation_manager.send_text", mock_send), \
             patch("src.services.conversation_manager.mark_as_read", AsyncMock()), \
             patch("src.services.conversation_manager.generate_response", mock_claude), \
             patch("src.services.conversation_manager.download_media", AsyncMock(return_value=None)), \
             patch("src.clients.audio_transcription.get_settings", return_value=MagicMock(groq_api_key="test-key")):

            manager = ConversationManager(db_session, mock_clinic_db)
            manager.clinic_repo.find_patient_by_phone = AsyncMock(return_value=None)
            manager.clinic_repo.find_lead_by_phone = AsyncMock(return_value=None)

            result = await manager.handle_incoming_message(
                phone="1199003344",
                content="[Audio recibido]",
                message_type="audio",
                wa_message_id="wamid.audio_dl_fail",
                media_id="media_audio_dl_fail",
            )

        assert result is not None
        assert "de nuevo" in result.lower() or "texto" in result.lower()
        mock_claude.assert_not_called()

    async def test_audio_transcription_fails_asks_for_text(self, db_session):
        """Transcripcion falla -> pide escribir por texto."""
        mock_send = AsyncMock()
        mock_claude = AsyncMock(return_value="No deberia llegar")
        mock_clinic_db = _make_clinic_db()

        with patch("src.services.conversation_manager.send_text", mock_send), \
             patch("src.services.conversation_manager.mark_as_read", AsyncMock()), \
             patch("src.services.conversation_manager.generate_response", mock_claude), \
             patch("src.services.conversation_manager.download_media", AsyncMock(return_value=b"\x00\x01")), \
             patch("src.clients.audio_transcription.get_settings", return_value=MagicMock(groq_api_key="test-key")), \
             patch("src.clients.audio_transcription._get_client") as mock_groq:

            # Groq devuelve error
            groq_response = MagicMock()
            groq_response.status_code = 500
            groq_response.text = "Internal error"
            mock_groq.return_value.post = AsyncMock(return_value=groq_response)

            manager = ConversationManager(db_session, mock_clinic_db)
            manager.clinic_repo.find_patient_by_phone = AsyncMock(return_value=None)
            manager.clinic_repo.find_lead_by_phone = AsyncMock(return_value=None)

            result = await manager.handle_incoming_message(
                phone="1199004455",
                content="[Audio recibido]",
                message_type="audio",
                wa_message_id="wamid.audio_groq_fail",
                media_id="media_audio_groq_fail",
            )

        assert result is not None
        assert "texto" in result.lower()
        mock_claude.assert_not_called()

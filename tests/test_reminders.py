"""
Tests para el sistema de recordatorios programados.

Cubre:
- Formateo de mensajes (sin DB, sin API)
- Modelo SentReminder y constraint UNIQUE (con DB rollback)
- Flujo de recordatorio de turno (mocks AppSheet + WhatsApp)
- Flujo de seguimiento de leads (mocks)
- Helper proactive_message
- Scheduler setup y distributed lock
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.models.conversation import Conversation, ContactType
from src.models.conversation_state import ConversationState, ConversationStatus
from src.models.message import Message, MessageRole, MessageType
from src.models.sent_reminder import ReminderType, ReminderStatus, SentReminder
from src.services.reminder_service import (
    _check_already_sent,
    _check_lead_responded,
    _format_aligner_message,
    _format_appointment_message,
    _format_birthday_message,
    _format_confirmation_message,
    _format_lead_followup_message,
    _format_professional_name,
    _format_review_message,
    _get_aligner_reminder_days,
    _resolve_patient_phone,
    process_aligner_reminders,
    process_appointment_confirmations,
    process_appointment_reminders,
    process_birthday_greetings,
    process_google_review_requests,
    process_lead_followups,
)


# =========================================================================
# FORMATTING TESTS (sin DB, sin API)
# =========================================================================

class TestFormatAppointmentMessage:
    """Test formateo de mensaje de recordatorio de turno."""

    def test_basic_format(self):
        """Mensaje estandar con todos los campos."""
        msg = _format_appointment_message(
            name="Garcia, Juan",
            appointment_date=date(2026, 3, 7),
            hora="09:00:00",
            profesional="Hatzerian, Cynthia",
        )
        assert "Juan" in msg
        assert "sabado 07 de marzo" in msg
        assert "9:00" in msg
        assert "Dra. Cynthia" in msg
        assert "SI" in msg
        assert "NO" in msg

    def test_name_without_comma(self):
        """Nombre sin formato 'Apellido, Nombre'."""
        msg = _format_appointment_message(
            name="Juan Garcia",
            appointment_date=date(2026, 3, 10),
            hora="14:30:00",
            profesional="Hatzerian, Cynthia",
        )
        assert "Juan Garcia" in msg

    def test_time_format_strips_seconds(self):
        """'14:30:00' se formatea como '14:30'."""
        msg = _format_appointment_message(
            name="Test, User",
            appointment_date=date(2026, 3, 10),
            hora="14:30:00",
            profesional="Hatzerian, Cynthia",
        )
        assert "14:30" in msg
        assert "14:30:00" not in msg

    def test_empty_name_uses_fallback(self):
        """Nombre vacio usa 'paciente'."""
        msg = _format_appointment_message(
            name="",
            appointment_date=date(2026, 3, 10),
            hora="10:00:00",
            profesional="Hatzerian, Cynthia",
        )
        assert "paciente" in msg

    def test_raw_time_format_fallback(self):
        """Si from_appsheet_time falla, usa hora tal cual."""
        msg = _format_appointment_message(
            name="Test, User",
            appointment_date=date(2026, 3, 10),
            hora="10hs",
            profesional="Hatzerian, Cynthia",
        )
        assert "10hs" in msg


class TestFormatProfessionalName:
    """Test formateo de nombre profesional."""

    def test_standard_format(self):
        assert _format_professional_name("Hatzerian, Cynthia") == "Dra. Cynthia"

    def test_mino_ana(self):
        assert _format_professional_name("Miño, Ana") == "Dra. Ana"

    def test_empty_returns_fallback(self):
        assert _format_professional_name("") == "el profesional"

    def test_name_without_comma(self):
        assert _format_professional_name("Cynthia Hatzerian") == "Cynthia Hatzerian"


class TestFormatLeadFollowupMessage:
    """Test formateo de mensajes de seguimiento de leads."""

    def test_day3_message(self):
        """Primer seguimiento (dia 3)."""
        msg = _format_lead_followup_message("Garcia, Juan", attempt=1)
        assert "Juan" in msg
        assert "charlamos" in msg

    def test_day7_message(self):
        """Segundo seguimiento (dia 7)."""
        msg = _format_lead_followup_message("Garcia, Juan", attempt=2)
        assert "Sofia de Stick" in msg
        assert "turnos disponibles" in msg

    def test_empty_name_day3(self):
        """Nombre vacio en dia 3."""
        msg = _format_lead_followup_message("", attempt=1)
        assert "Hola " in msg
        # No debe tener doble espacio o nombre raro
        assert "Hola  " not in msg


# =========================================================================
# MODELO SENT_REMINDER (con DB fixture rollback)
# =========================================================================

class TestSentReminderModel:
    """Tests del modelo SentReminder con la DB real (rollback al final)."""

    @pytest.mark.asyncio
    async def test_create_reminder(self, db_session):
        """Crear un recordatorio basico."""
        reminder = SentReminder(
            reminder_type=ReminderType.APPOINTMENT_24H,
            reference_id="SES-001",
            phone="1123266671",
            attempt=1,
            status=ReminderStatus.SENT,
            message_sent="Hola, recordatorio...",
            target_date=date(2026, 3, 7),
        )
        db_session.add(reminder)
        await db_session.flush()

        assert reminder.id is not None
        assert reminder.reminder_type == ReminderType.APPOINTMENT_24H
        assert reminder.created_at is not None

    @pytest.mark.asyncio
    async def test_unique_constraint_prevents_duplicate(self, db_session):
        """Mismo (type, reference_id, attempt) lanza IntegrityError."""
        r1 = SentReminder(
            reminder_type=ReminderType.APPOINTMENT_24H,
            reference_id="SES-001",
            phone="1123266671",
            attempt=1,
            status=ReminderStatus.SENT,
        )
        db_session.add(r1)
        await db_session.flush()

        r2 = SentReminder(
            reminder_type=ReminderType.APPOINTMENT_24H,
            reference_id="SES-001",
            phone="1123266671",
            attempt=1,
            status=ReminderStatus.SENT,
        )
        db_session.add(r2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_different_attempts_allowed(self, db_session):
        """Mismo lead con attempt=1 y attempt=2 es OK."""
        r1 = SentReminder(
            reminder_type=ReminderType.LEAD_FOLLOWUP_DAY3,
            reference_id="LEAD-42",
            phone="1199887766",
            attempt=1,
            status=ReminderStatus.SENT,
        )
        r2 = SentReminder(
            reminder_type=ReminderType.LEAD_FOLLOWUP_DAY7,
            reference_id="LEAD-42",
            phone="1199887766",
            attempt=2,
            status=ReminderStatus.SENT,
        )
        db_session.add(r1)
        db_session.add(r2)
        await db_session.flush()

        assert r1.id is not None
        assert r2.id is not None
        assert r1.id != r2.id

    @pytest.mark.asyncio
    async def test_different_types_same_ref(self, db_session):
        """Diferentes tipos con mismo reference_id es OK."""
        r1 = SentReminder(
            reminder_type=ReminderType.APPOINTMENT_24H,
            reference_id="SES-001",
            phone="1123266671",
            attempt=1,
            status=ReminderStatus.SENT,
        )
        r2 = SentReminder(
            reminder_type=ReminderType.LEAD_FOLLOWUP_DAY3,
            reference_id="SES-001",
            phone="1123266671",
            attempt=1,
            status=ReminderStatus.SENT,
        )
        db_session.add(r1)
        db_session.add(r2)
        await db_session.flush()

        assert r1.id is not None
        assert r2.id is not None


# =========================================================================
# CHECK ALREADY SENT
# =========================================================================

class TestCheckAlreadySent:
    """Test del pre-check de duplicados."""

    @pytest.mark.asyncio
    async def test_not_sent_returns_false(self, db_session):
        result = await _check_already_sent(
            db_session, ReminderType.APPOINTMENT_24H, "SES-999", 1,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_already_sent_returns_true(self, db_session):
        r = SentReminder(
            reminder_type=ReminderType.APPOINTMENT_24H,
            reference_id="SES-001",
            phone="1123266671",
            attempt=1,
            status=ReminderStatus.SENT,
        )
        db_session.add(r)
        await db_session.flush()

        result = await _check_already_sent(
            db_session, ReminderType.APPOINTMENT_24H, "SES-001", 1,
        )
        assert result is True


# =========================================================================
# RESOLVE PATIENT PHONE
# =========================================================================

class TestResolvePatientPhone:
    """Test de resolucion de telefono del paciente."""

    @pytest.mark.asyncio
    async def test_phone_from_session_data(self, db_session):
        """Si la sesion trae telefono, usarlo directamente."""
        phone = await _resolve_patient_phone(
            db_session,
            patient_id="PAT-001",
            session_data={"Telefono (Whatsapp)": "+5491123266671"},
        )
        assert phone == "1123266671"

    @pytest.mark.asyncio
    async def test_phone_from_local_conversation(self, db_session):
        """Si la conversacion local tiene el patient_id, usar ese phone."""
        conv = Conversation(
            phone="1199887766",
            contact_type=ContactType.PACIENTE,
            patient_id="PAT-002",
            patient_name="Test Patient",
        )
        db_session.add(conv)
        await db_session.flush()

        phone = await _resolve_patient_phone(
            db_session,
            patient_id="PAT-002",
            session_data={},
        )
        assert phone == "1199887766"

    @pytest.mark.asyncio
    async def test_phone_from_appsheet_fallback(self, db_session):
        """Si no hay datos locales, consultar AppSheet."""
        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Paciente": "PAT-003",
            "Telefono (Whatsapp)": "+5491155443322",
        }])

        with patch(
            "src.services.reminder_service.get_appsheet_client",
            return_value=mock_appsheet,
        ):
            phone = await _resolve_patient_phone(
                db_session,
                patient_id="PAT-003",
                session_data={},
            )
        assert phone == "1155443322"

    @pytest.mark.asyncio
    async def test_phone_not_found_returns_none(self, db_session):
        """Si no se encuentra telefono en ninguna fuente, retorna None."""
        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[])

        with patch(
            "src.services.reminder_service.get_appsheet_client",
            return_value=mock_appsheet,
        ):
            phone = await _resolve_patient_phone(
                db_session,
                patient_id="PAT-NOEXISTE",
                session_data={},
            )
        assert phone is None


# =========================================================================
# CHECK LEAD RESPONDED
# =========================================================================

class TestCheckLeadResponded:
    """Test si un lead respondio."""

    @pytest.mark.asyncio
    async def test_no_conversation_returns_false(self, db_session):
        result = await _check_lead_responded(db_session, "9999999999")
        assert result is False

    @pytest.mark.asyncio
    async def test_conversation_without_user_messages_returns_false(self, db_session):
        """Conversacion existe pero solo tiene mensajes ASSISTANT."""
        conv = Conversation(
            phone="1199887766",
            contact_type=ContactType.LEAD,
        )
        db_session.add(conv)
        await db_session.flush()

        msg = Message(
            conversation_id=conv.id,
            role=MessageRole.ASSISTANT,
            content="Hola, recordatorio...",
            message_type=MessageType.TEXT,
        )
        db_session.add(msg)
        await db_session.flush()

        result = await _check_lead_responded(db_session, "1199887766")
        assert result is False

    @pytest.mark.asyncio
    async def test_conversation_with_user_messages_returns_true(self, db_session):
        """Conversacion con mensajes USER → lead respondio."""
        conv = Conversation(
            phone="1199887766",
            contact_type=ContactType.LEAD,
        )
        db_session.add(conv)
        await db_session.flush()

        msg = Message(
            conversation_id=conv.id,
            role=MessageRole.USER,
            content="Si, quiero un turno",
            message_type=MessageType.TEXT,
        )
        db_session.add(msg)
        await db_session.flush()

        result = await _check_lead_responded(db_session, "1199887766")
        assert result is True


# =========================================================================
# FLUJO COMPLETO: RECORDATORIO DE TURNO
# =========================================================================

class TestAppointmentReminderFlow:
    """Tests de integracion del flujo de recordatorio de turno."""

    @pytest.mark.asyncio
    async def test_sends_reminder_for_tomorrows_session(self, db_session):
        """Happy path: sesion de mañana → envia recordatorio."""
        tomorrow = date.today() + timedelta(days=1)

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Sesion": "SES-001",
            "ID PACIENTE": "PAT-001",
            "Paciente": "Garcia, Juan",
            "Hora Sesion": "15:00:00",
            "Profesional Asignado": "Hatzerian, Cynthia",
            "Telefono (Whatsapp)": "+5491123266671",
        }])

        mock_send = AsyncMock(return_value={"status": "ok", "wa_message_id": "wamid.123"})

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=tomorrow - timedelta(days=1)), \
             patch("src.services.reminder_service.to_appsheet_date") as mock_to_date, \
             patch("src.db.session.get_session_factory", return_value=mock_factory), \
             patch("src.services.proactive_message.send_text", mock_send):

            mock_to_date.return_value = tomorrow.strftime("%m/%d/%Y")

            result = await process_appointment_reminders()

        assert result["sent"] == 1
        assert result["skipped"] == 0
        assert result["errors"] == 0

        # Verificar que se inserto el sent_reminder
        stmt = select(SentReminder).where(SentReminder.reference_id == "SES-001")
        db_result = await db_session.execute(stmt)
        reminder = db_result.scalar_one_or_none()
        assert reminder is not None
        assert reminder.status == ReminderStatus.SENT
        assert "Juan" in reminder.message_sent

    @pytest.mark.asyncio
    async def test_skips_already_sent_appointment(self, db_session):
        """Si ya se envio el recordatorio, skip."""
        # Pre-insertar un recordatorio ya enviado
        existing = SentReminder(
            reminder_type=ReminderType.APPOINTMENT_24H,
            reference_id="SES-002",
            phone="1123266671",
            attempt=1,
            status=ReminderStatus.SENT,
            message_sent="Ya enviado",
        )
        db_session.add(existing)
        await db_session.flush()

        tomorrow = date.today() + timedelta(days=1)

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Sesion": "SES-002",
            "ID PACIENTE": "PAT-001",
            "Paciente": "Garcia, Juan",
            "Hora Sesion": "15:00:00",
            "Profesional Asignado": "Hatzerian, Cynthia",
            "Telefono (Whatsapp)": "+5491123266671",
        }])

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=tomorrow - timedelta(days=1)), \
             patch("src.services.reminder_service.to_appsheet_date") as mock_to_date, \
             patch("src.db.session.get_session_factory", return_value=mock_factory):

            mock_to_date.return_value = tomorrow.strftime("%m/%d/%Y")

            result = await process_appointment_reminders()

        assert result["sent"] == 0
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_handles_whatsapp_failure(self, db_session):
        """WhatsApp falla → status=FAILED."""
        tomorrow = date.today() + timedelta(days=1)

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Sesion": "SES-003",
            "ID PACIENTE": "PAT-001",
            "Paciente": "Garcia, Juan",
            "Hora Sesion": "15:00:00",
            "Profesional Asignado": "Hatzerian, Cynthia",
            "Telefono (Whatsapp)": "+5491123266671",
        }])

        mock_send = AsyncMock(return_value={"status": "error", "error": "Token expired"})

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=tomorrow - timedelta(days=1)), \
             patch("src.services.reminder_service.to_appsheet_date") as mock_to_date, \
             patch("src.db.session.get_session_factory", return_value=mock_factory), \
             patch("src.services.proactive_message.send_text", mock_send):

            mock_to_date.return_value = tomorrow.strftime("%m/%d/%Y")

            result = await process_appointment_reminders()

        assert result["errors"] == 1

        # Verificar status FAILED en DB
        stmt = select(SentReminder).where(SentReminder.reference_id == "SES-003")
        db_result = await db_session.execute(stmt)
        reminder = db_result.scalar_one_or_none()
        assert reminder is not None
        assert reminder.status == ReminderStatus.FAILED

    @pytest.mark.asyncio
    async def test_no_sessions_tomorrow_does_nothing(self):
        """Sin sesiones para mañana → 0 envios."""
        tomorrow = date.today() + timedelta(days=1)

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[])

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=tomorrow - timedelta(days=1)), \
             patch("src.services.reminder_service.to_appsheet_date") as mock_to_date:

            mock_to_date.return_value = tomorrow.strftime("%m/%d/%Y")

            result = await process_appointment_reminders()

        assert result["sent"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0


# =========================================================================
# FLUJO COMPLETO: SEGUIMIENTO DE LEADS
# =========================================================================

class TestLeadFollowupFlow:
    """Tests de integracion del flujo de seguimiento de leads."""

    @pytest.mark.asyncio
    async def test_day3_sends_first_followup(self, db_session):
        """Lead Nuevo hace 3 dias → envia primer seguimiento."""
        today = date.today()

        mock_appsheet = AsyncMock()
        # day3 find retorna un lead, day7 retorna vacio
        mock_appsheet.find = AsyncMock(side_effect=[
            [{  # day 3 leads
                "ID Lead": "LEAD-42",
                "Apellido y Nombre": "Perez, Maria",
                "Telefono (Whatsapp)": "+5491199887766",
                "Fecha Creacion": (today - timedelta(days=3)).strftime("%m/%d/%Y"),
                "Estado del Lead (Temp)": "Nuevo",
            }],
            [],  # day 7 leads
        ])
        mock_appsheet.edit = AsyncMock(return_value=[])

        mock_send = AsyncMock(return_value={"status": "ok", "wa_message_id": "wamid.456"})

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today), \
             patch("src.services.reminder_service.to_appsheet_date") as mock_to_date, \
             patch("src.db.session.get_session_factory", return_value=mock_factory), \
             patch("src.services.proactive_message.send_text", mock_send):

            mock_to_date.side_effect = lambda d: d.strftime("%m/%d/%Y")

            result = await process_lead_followups()

        assert result["sent"] == 1
        assert result["skipped"] == 0

        # Verificar que se inserto el sent_reminder
        stmt = select(SentReminder).where(SentReminder.reference_id == "LEAD-42")
        db_result = await db_session.execute(stmt)
        reminder = db_result.scalar_one_or_none()
        assert reminder is not None
        assert reminder.reminder_type == ReminderType.LEAD_FOLLOWUP_DAY3
        assert reminder.attempt == 1

    @pytest.mark.asyncio
    async def test_skips_lead_who_responded(self, db_session):
        """Lead que respondio → skip + CANCELLED."""
        # Crear conversacion con mensaje USER del lead
        conv = Conversation(
            phone="1199887766",
            contact_type=ContactType.LEAD,
        )
        db_session.add(conv)
        await db_session.flush()

        msg = Message(
            conversation_id=conv.id,
            role=MessageRole.USER,
            content="Si, quiero un turno",
            message_type=MessageType.TEXT,
        )
        db_session.add(msg)
        await db_session.flush()

        today = date.today()

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(side_effect=[
            [{
                "ID Lead": "LEAD-99",
                "Apellido y Nombre": "Lopez, Ana",
                "Telefono (Whatsapp)": "+5491199887766",
                "Fecha Creacion": (today - timedelta(days=3)).strftime("%m/%d/%Y"),
                "Estado del Lead (Temp)": "Nuevo",
            }],
            [],
        ])

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today), \
             patch("src.services.reminder_service.to_appsheet_date") as mock_to_date, \
             patch("src.db.session.get_session_factory", return_value=mock_factory):

            mock_to_date.side_effect = lambda d: d.strftime("%m/%d/%Y")

            result = await process_lead_followups()

        assert result["sent"] == 0
        assert result["skipped"] == 1

        # Verificar CANCELLED en DB
        stmt = select(SentReminder).where(SentReminder.reference_id == "LEAD-99")
        db_result = await db_session.execute(stmt)
        reminder = db_result.scalar_one_or_none()
        assert reminder is not None
        assert reminder.status == ReminderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_day7_sends_second_followup(self, db_session):
        """Lead Contactado Frio hace 7 dias → envia segundo seguimiento."""
        today = date.today()

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(side_effect=[
            [],  # day 3 leads
            [{   # day 7 leads
                "ID Lead": "LEAD-55",
                "Apellido y Nombre": "Gomez, Carlos",
                "Telefono (Whatsapp)": "+5491177665544",
                "Fecha Creacion": (today - timedelta(days=7)).strftime("%m/%d/%Y"),
                "Estado del Lead (Temp)": "Contactado Frio",
            }],
        ])
        mock_appsheet.edit = AsyncMock(return_value=[])

        mock_send = AsyncMock(return_value={"status": "ok", "wa_message_id": "wamid.789"})

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today), \
             patch("src.services.reminder_service.to_appsheet_date") as mock_to_date, \
             patch("src.db.session.get_session_factory", return_value=mock_factory), \
             patch("src.services.proactive_message.send_text", mock_send):

            mock_to_date.side_effect = lambda d: d.strftime("%m/%d/%Y")

            result = await process_lead_followups()

        assert result["sent"] == 1

        # Verificar tipo y attempt
        stmt = select(SentReminder).where(SentReminder.reference_id == "LEAD-55")
        db_result = await db_session.execute(stmt)
        reminder = db_result.scalar_one_or_none()
        assert reminder is not None
        assert reminder.reminder_type == ReminderType.LEAD_FOLLOWUP_DAY7
        assert reminder.attempt == 2

        # Verificar que actualizo estado en AppSheet
        mock_appsheet.edit.assert_called_once()
        edit_args = mock_appsheet.edit.call_args
        assert edit_args[0][0] == "BBDD LEADS"
        assert edit_args[0][1][0]["Estado del Lead (Temp)"] == "Cerrada Perdida"


# =========================================================================
# PROACTIVE MESSAGE HELPER
# =========================================================================

class TestProactiveMessage:
    """Tests del helper de mensaje proactivo."""

    @pytest.mark.asyncio
    async def test_creates_conversation_if_not_exists(self, db_session):
        """Telefono nuevo → crea conversacion + state + mensaje."""
        from src.services.proactive_message import send_proactive_message

        mock_send = AsyncMock(return_value={"status": "ok", "wa_message_id": "wamid.test"})

        with patch("src.services.proactive_message.send_text", mock_send):
            result = await send_proactive_message(
                db=db_session,
                phone_10="1188776655",
                text="Hola, recordatorio de turno",
                patient_name="Test Patient",
                patient_id="PAT-TEST",
            )

        assert result["status"] == "ok"

        # Verificar conversacion creada
        stmt = select(Conversation).where(Conversation.phone == "1188776655")
        db_result = await db_session.execute(stmt)
        conv = db_result.scalar_one_or_none()
        assert conv is not None
        assert conv.patient_name == "Test Patient"
        assert conv.patient_id == "PAT-TEST"

        # Verificar state creado
        stmt = select(ConversationState).where(
            ConversationState.conversation_id == conv.id
        )
        db_result = await db_session.execute(stmt)
        state = db_result.scalar_one_or_none()
        assert state is not None
        assert state.status == ConversationStatus.BOT_ACTIVE

    @pytest.mark.asyncio
    async def test_reuses_existing_conversation(self, db_session):
        """Telefono existente → agrega mensaje a conversacion existente."""
        from src.services.proactive_message import send_proactive_message

        # Pre-crear conversacion
        conv = Conversation(
            phone="1188776655",
            contact_type=ContactType.PACIENTE,
            patient_name="Existing Patient",
        )
        db_session.add(conv)
        await db_session.flush()
        conv_id = conv.id

        mock_send = AsyncMock(return_value={"status": "ok", "wa_message_id": "wamid.test2"})

        with patch("src.services.proactive_message.send_text", mock_send):
            await send_proactive_message(
                db=db_session,
                phone_10="1188776655",
                text="Segundo recordatorio",
            )

        # Verificar que NO creo nueva conversacion
        stmt = select(Conversation).where(Conversation.phone == "1188776655")
        db_result = await db_session.execute(stmt)
        convs = db_result.scalars().all()
        assert len(convs) == 1
        assert convs[0].id == conv_id

    @pytest.mark.asyncio
    async def test_saves_as_assistant_role(self, db_session):
        """Mensaje guardado con role=ASSISTANT."""
        from src.services.proactive_message import send_proactive_message

        mock_send = AsyncMock(return_value={"status": "ok", "wa_message_id": "wamid.test3"})

        with patch("src.services.proactive_message.send_text", mock_send):
            await send_proactive_message(
                db=db_session,
                phone_10="1166554433",
                text="Recordatorio automatico",
            )

        # Verificar mensaje guardado como ASSISTANT
        stmt = (
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.phone == "1166554433")
        )
        db_result = await db_session.execute(stmt)
        msg = db_result.scalar_one_or_none()
        assert msg is not None
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Recordatorio automatico"
        assert msg.message_type == MessageType.TEXT


# =========================================================================
# SCHEDULER
# =========================================================================

class TestScheduler:
    """Tests del scheduler APScheduler."""

    @pytest.mark.asyncio
    async def test_scheduler_disabled(self):
        """scheduler_enabled=False → no arranca."""
        from src.services.scheduler import start_scheduler, get_scheduler, _scheduler

        mock_settings = MagicMock()
        mock_settings.scheduler_enabled = False

        with patch("src.services.scheduler.get_settings", return_value=mock_settings):
            await start_scheduler()

        # Scheduler no deberia estar activo
        # (get_scheduler puede ser None si no se inicio)

    @pytest.mark.asyncio
    async def test_scheduler_starts_with_jobs(self):
        """scheduler_enabled=True → 6 jobs registrados."""
        from src.services.scheduler import start_scheduler, stop_scheduler
        import src.services.scheduler as sched_module

        mock_settings = MagicMock()
        mock_settings.scheduler_enabled = True
        mock_settings.scheduler_appointment_cron_hour = 10
        mock_settings.scheduler_lead_followup_cron_hour = 11
        mock_settings.scheduler_confirmation_interval_minutes = 60
        mock_settings.scheduler_birthday_cron_hour = 9
        mock_settings.scheduler_aligner_cron_hour = 10
        mock_settings.scheduler_review_cron_hour = 14
        mock_settings.scheduler_lock_ttl_seconds = 600

        with patch("src.services.scheduler.get_settings", return_value=mock_settings):
            await start_scheduler()

        scheduler = sched_module._scheduler
        assert scheduler is not None
        assert len(scheduler.get_jobs()) == 6

        job_ids = [j.id for j in scheduler.get_jobs()]
        assert "appointment_reminders" in job_ids
        assert "lead_followup" in job_ids
        assert "appointment_confirmations" in job_ids
        assert "birthday_greetings" in job_ids
        assert "aligner_reminders" in job_ids
        assert "google_review_requests" in job_ids

        # Cleanup
        await stop_scheduler()

    @pytest.mark.asyncio
    async def test_lock_prevents_concurrent_execution(self):
        """Redis lock held → job se skipea."""
        from src.services.scheduler import _run_with_lock

        mock_func = AsyncMock()
        mock_redis = AsyncMock()
        # Lock ya tomado (set con nx=True retorna None/False)
        mock_redis.set = AsyncMock(return_value=False)

        mock_settings = MagicMock()
        mock_settings.scheduler_lock_ttl_seconds = 600

        async def fake_get_redis():
            return mock_redis

        with patch("src.services.scheduler.get_settings", return_value=mock_settings), \
             patch("src.clients.redis_client.get_redis", fake_get_redis):
            await _run_with_lock("test:lock", mock_func)

        # La funcion NO deberia haberse ejecutado
        mock_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_runs_without_redis(self):
        """Redis no disponible → ejecuta de todos modos."""
        from src.services.scheduler import _run_with_lock

        mock_func = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.scheduler_lock_ttl_seconds = 600

        async def fake_get_redis():
            return None

        with patch("src.services.scheduler.get_settings", return_value=mock_settings), \
             patch("src.clients.redis_client.get_redis", fake_get_redis):
            await _run_with_lock("test:lock", mock_func)

        # La funcion SI deberia haberse ejecutado
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_lock_released_on_error(self):
        """Si la funcion falla, el lock se libera."""
        from src.services.scheduler import _run_with_lock

        mock_func = AsyncMock(side_effect=Exception("boom"))
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock()

        mock_settings = MagicMock()
        mock_settings.scheduler_lock_ttl_seconds = 600

        async def fake_get_redis():
            return mock_redis

        with patch("src.services.scheduler.get_settings", return_value=mock_settings), \
             patch("src.clients.redis_client.get_redis", fake_get_redis):
            # No deberia propagar la excepcion
            await _run_with_lock("test:lock", mock_func)

        # El lock se intento liberar
        mock_redis.delete.assert_called_once_with("test:lock")


# =========================================================================
# FORMATEO MENSAJES NUEVOS (sin DB, sin API)
# =========================================================================

class TestFormatConfirmationMessage:
    """Test formateo de mensaje de confirmacion de turno."""

    def test_basic_format(self):
        """Mensaje con todos los campos."""
        msg = _format_confirmation_message(
            name="Garcia, Juan",
            appointment_date=date(2026, 3, 10),
            hora="14:30:00",
            profesional="Hatzerian, Cynthia",
        )
        assert "Juan" in msg
        assert "martes 10 de marzo" in msg
        assert "14:30" in msg
        assert "Dra. Cynthia" in msg
        assert "Virrey del Pino" in msg
        assert "confirmarlo" in msg

    def test_empty_name_uses_fallback(self):
        msg = _format_confirmation_message(
            name="",
            appointment_date=date(2026, 3, 10),
            hora="10:00:00",
            profesional="Hatzerian, Cynthia",
        )
        assert "paciente" in msg

    def test_does_not_contain_si_no(self):
        """Confirmacion NO pide SI/NO (eso es el recordatorio 24h)."""
        msg = _format_confirmation_message(
            name="Garcia, Juan",
            appointment_date=date(2026, 3, 10),
            hora="10:00:00",
            profesional="Hatzerian, Cynthia",
        )
        assert "SI" not in msg
        assert "NO" not in msg


class TestFormatBirthdayMessage:
    """Test formateo de mensaje de cumpleaños."""

    def test_basic_format(self):
        msg = _format_birthday_message("Garcia, Juan")
        assert "Juan" in msg
        assert "cumpleaños" in msg
        assert "STICK" in msg

    def test_empty_name(self):
        msg = _format_birthday_message("")
        assert "paciente" in msg
        assert "cumpleaños" in msg


class TestFormatAlignerMessage:
    """Test formateo de mensaje de cambio de alineadores."""

    def test_basic_format(self):
        msg = _format_aligner_message("Garcia, Juan")
        assert "Juan" in msg
        assert "alineadores" in msg
        assert "20 y 22 horas" in msg

    def test_empty_name(self):
        msg = _format_aligner_message("")
        assert "paciente" in msg
        assert "alineadores" in msg


class TestFormatReviewMessage:
    """Test formateo de mensaje de solicitud de review."""

    def test_basic_format(self):
        link = "https://g.page/r/CXyr_5_Wv5_7EBM/review"
        msg = _format_review_message("Garcia, Juan", link)
        assert "Juan" in msg
        assert link in msg
        assert "Google" in msg

    def test_empty_name(self):
        link = "https://g.page/test"
        msg = _format_review_message("", link)
        assert "paciente" in msg
        assert link in msg


class TestGetAlignerReminderDays:
    """Test logica de timing de recordatorio de alineadores."""

    def test_cycle_very_short_no_reminder(self):
        """Ciclo < 22 dias → no enviar."""
        assert _get_aligner_reminder_days(20) == []

    def test_cycle_short_day_12(self):
        """Ciclo 22-26 dias → dia 12."""
        assert _get_aligner_reminder_days(22) == [12]
        assert _get_aligner_reminder_days(26) == [12]

    def test_cycle_standard_day_15(self):
        """Ciclo 27-34 dias → dia 15."""
        assert _get_aligner_reminder_days(27) == [15]
        assert _get_aligner_reminder_days(30) == [15]
        assert _get_aligner_reminder_days(34) == [15]

    def test_cycle_long_days_15_and_30(self):
        """Ciclo 34+ dias → dias 15 y 30."""
        assert _get_aligner_reminder_days(35) == [15, 30]
        assert _get_aligner_reminder_days(45) == [15, 30]


# =========================================================================
# FLUJO COMPLETO: CONFIRMACIÓN DE TURNO
# =========================================================================

class TestAppointmentConfirmationFlow:
    """Tests del flujo de confirmacion de turno."""

    @pytest.mark.asyncio
    async def test_sends_confirmation_for_new_session(self, db_session):
        """Happy path: sesion futura → envia confirmacion."""
        future_date = date.today() + timedelta(days=5)
        future_appsheet = future_date.strftime("%m/%d/%Y")

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Sesion": "SES-CONF-001",
            "ID PACIENTE": "PAT-001",
            "Paciente": "Garcia, Juan",
            "Hora Sesion": "15:00:00",
            "Profesional Asignado": "Hatzerian, Cynthia",
            "Fecha de Sesion": future_appsheet,
            "Telefono (Whatsapp)": "+5491123266671",
        }])

        mock_send = AsyncMock(return_value={"status": "ok", "wa_message_id": "wamid.conf1"})

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=date.today()), \
             patch("src.db.session.get_session_factory", return_value=mock_factory), \
             patch("src.services.proactive_message.send_text", mock_send):

            result = await process_appointment_confirmations()

        assert result["sent"] == 1
        assert result["skipped"] == 0

        # Verificar sent_reminder creado
        stmt = select(SentReminder).where(SentReminder.reference_id == "SES-CONF-001")
        db_result = await db_session.execute(stmt)
        reminder = db_result.scalar_one_or_none()
        assert reminder is not None
        assert reminder.reminder_type == ReminderType.APPOINTMENT_CONFIRMATION
        assert "Virrey del Pino" in reminder.message_sent

    @pytest.mark.asyncio
    async def test_skips_already_confirmed_session(self, db_session):
        """Sesion ya confirmada → skip."""
        existing = SentReminder(
            reminder_type=ReminderType.APPOINTMENT_CONFIRMATION,
            reference_id="SES-CONF-002",
            phone="1123266671",
            attempt=1,
            status=ReminderStatus.SENT,
        )
        db_session.add(existing)
        await db_session.flush()

        future_date = date.today() + timedelta(days=5)

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Sesion": "SES-CONF-002",
            "ID PACIENTE": "PAT-001",
            "Paciente": "Garcia, Juan",
            "Hora Sesion": "15:00:00",
            "Profesional Asignado": "Hatzerian, Cynthia",
            "Fecha de Sesion": future_date.strftime("%m/%d/%Y"),
            "Telefono (Whatsapp)": "+5491123266671",
        }])

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=date.today()), \
             patch("src.db.session.get_session_factory", return_value=mock_factory):

            result = await process_appointment_confirmations()

        assert result["sent"] == 0
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_skips_past_sessions(self):
        """Sesiones pasadas → no enviar confirmacion."""
        past_date = date.today() - timedelta(days=2)
        past_appsheet = past_date.strftime("%m/%d/%Y")

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Sesion": "SES-PAST-001",
            "ID PACIENTE": "PAT-001",
            "Paciente": "Garcia, Juan",
            "Hora Sesion": "15:00:00",
            "Profesional Asignado": "Hatzerian, Cynthia",
            "Fecha de Sesion": past_appsheet,
            "Telefono (Whatsapp)": "+5491123266671",
        }])

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=date.today()):

            result = await process_appointment_confirmations()

        assert result["sent"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0


# =========================================================================
# FLUJO COMPLETO: SALUDO DE CUMPLEAÑOS
# =========================================================================

class TestBirthdayGreetingFlow:
    """Tests del flujo de saludo de cumpleaños."""

    @pytest.mark.asyncio
    async def test_sends_birthday_on_matching_date(self, db_session):
        """Paciente con cumpleaños hoy → envia saludo."""
        today = date(2026, 3, 15)

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Paciente": "PAT-BD-001",
            "Paciente": "Garcia, Juan",
            "Telefono (Whatsapp)": "+5491123266671",
            "Estado del Paciente": "Activo",
            "Fecha Nacimiento": "03/15/1990",  # mismo mes/dia que today
        }])

        mock_send = AsyncMock(return_value={"status": "ok", "wa_message_id": "wamid.bd1"})

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today), \
             patch("src.db.session.get_session_factory", return_value=mock_factory), \
             patch("src.services.proactive_message.send_text", mock_send):

            result = await process_birthday_greetings()

        assert result["sent"] == 1

        # Verificar reference_id incluye año
        stmt = select(SentReminder).where(
            SentReminder.reference_id == "PAT-BD-001_2026"
        )
        db_result = await db_session.execute(stmt)
        reminder = db_result.scalar_one_or_none()
        assert reminder is not None
        assert reminder.reminder_type == ReminderType.BIRTHDAY_GREETING
        assert "cumpleaños" in reminder.message_sent

    @pytest.mark.asyncio
    async def test_skips_non_birthday(self):
        """Paciente con cumpleaños en otro dia → skip."""
        today = date(2026, 3, 15)

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Paciente": "PAT-BD-002",
            "Paciente": "Garcia, Juan",
            "Telefono (Whatsapp)": "+5491123266671",
            "Fecha Nacimiento": "06/20/1990",  # Junio 20, no hoy
        }])

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today):

            result = await process_birthday_greetings()

        assert result["sent"] == 0
        assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_skips_already_sent_this_year(self, db_session):
        """Saludo ya enviado este año → skip."""
        today = date(2026, 3, 15)

        # Pre-insertar saludo ya enviado
        existing = SentReminder(
            reminder_type=ReminderType.BIRTHDAY_GREETING,
            reference_id="PAT-BD-003_2026",
            phone="1123266671",
            attempt=1,
            status=ReminderStatus.SENT,
        )
        db_session.add(existing)
        await db_session.flush()

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Paciente": "PAT-BD-003",
            "Paciente": "Garcia, Juan",
            "Telefono (Whatsapp)": "+5491123266671",
            "Fecha Nacimiento": "03/15/1990",
        }])

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today), \
             patch("src.db.session.get_session_factory", return_value=mock_factory):

            result = await process_birthday_greetings()

        assert result["sent"] == 0
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_skips_patient_without_birthday(self):
        """Paciente sin Fecha Nacimiento → skip."""
        today = date(2026, 3, 15)

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Paciente": "PAT-BD-004",
            "Paciente": "Garcia, Juan",
            "Telefono (Whatsapp)": "+5491123266671",
            "Fecha Nacimiento": "",  # Vacio
        }])

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today):

            result = await process_birthday_greetings()

        assert result["sent"] == 0


# =========================================================================
# FLUJO COMPLETO: ALINEADORES
# =========================================================================

class TestAlignerReminderFlow:
    """Tests del flujo de recordatorio de cambio de alineadores."""

    @pytest.mark.asyncio
    async def test_sends_aligner_reminder_at_day_15(self, db_session):
        """Ciclo estandar, dia 15 → envia recordatorio."""
        today = date(2026, 3, 15)
        last_realized_date = today - timedelta(days=15)  # 15 dias atras
        next_planned_date = today + timedelta(days=15)  # 30 dias entre sesiones

        mock_appsheet = AsyncMock()
        # Primer find: sesiones futuras Planificada/Confirmada
        # Segundo find: sesiones realizadas del paciente
        mock_appsheet.find = AsyncMock(side_effect=[
            [{  # Proxima sesion planificada
                "ID Sesion": "SES-AL-NEXT",
                "ID PACIENTE": "PAT-AL-001",
                "Paciente": "Garcia, Juan",
                "Tratamiento": "Alineadores",
                "Fecha de Sesion": next_planned_date.strftime("%m/%d/%Y"),
                "Estado de Sesion": "Planificada",
                "Telefono (Whatsapp)": "+5491123266671",
            }],
            [{  # Ultima sesion realizada
                "ID Sesion": "SES-AL-LAST",
                "ID PACIENTE": "PAT-AL-001",
                "Paciente": "Garcia, Juan",
                "Tratamiento": "Alineadores",
                "Fecha de Sesion": last_realized_date.strftime("%m/%d/%Y"),
                "Estado de Sesion": "Realizada",
            }],
        ])

        mock_send = AsyncMock(return_value={"status": "ok", "wa_message_id": "wamid.al1"})

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today), \
             patch("src.db.session.get_session_factory", return_value=mock_factory), \
             patch("src.services.proactive_message.send_text", mock_send):

            result = await process_aligner_reminders()

        assert result["sent"] == 1

        # Verificar reference_id
        stmt = select(SentReminder).where(
            SentReminder.reference_id == "SES-AL-LAST_day15"
        )
        db_result = await db_session.execute(stmt)
        reminder = db_result.scalar_one_or_none()
        assert reminder is not None
        assert reminder.reminder_type == ReminderType.ALIGNER_CHANGE
        assert "alineadores" in reminder.message_sent

    @pytest.mark.asyncio
    async def test_aligner_cycle_short_sends_day_12(self, db_session):
        """Ciclo corto (24 dias), dia 12 → envia."""
        today = date(2026, 3, 12)
        last_realized_date = today - timedelta(days=12)
        next_planned_date = last_realized_date + timedelta(days=24)  # 24 dias entre sesiones

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(side_effect=[
            [{
                "ID Sesion": "SES-AL-SHORT-NEXT",
                "ID PACIENTE": "PAT-AL-002",
                "Paciente": "Lopez, Maria",
                "Tratamiento": "Alineadores",
                "Fecha de Sesion": next_planned_date.strftime("%m/%d/%Y"),
                "Estado de Sesion": "Planificada",
                "Telefono (Whatsapp)": "+5491199887766",
            }],
            [{
                "ID Sesion": "SES-AL-SHORT-LAST",
                "ID PACIENTE": "PAT-AL-002",
                "Paciente": "Lopez, Maria",
                "Tratamiento": "Alineadores",
                "Fecha de Sesion": last_realized_date.strftime("%m/%d/%Y"),
                "Estado de Sesion": "Realizada",
            }],
        ])

        mock_send = AsyncMock(return_value={"status": "ok", "wa_message_id": "wamid.al2"})

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today), \
             patch("src.db.session.get_session_factory", return_value=mock_factory), \
             patch("src.services.proactive_message.send_text", mock_send):

            result = await process_aligner_reminders()

        assert result["sent"] == 1

        stmt = select(SentReminder).where(
            SentReminder.reference_id == "SES-AL-SHORT-LAST_day12"
        )
        db_result = await db_session.execute(stmt)
        reminder = db_result.scalar_one_or_none()
        assert reminder is not None

    @pytest.mark.asyncio
    async def test_aligner_no_realized_sessions_skips(self):
        """Sin sesiones realizadas → skip."""
        today = date(2026, 3, 15)
        future = today + timedelta(days=10)

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(side_effect=[
            [{  # Proxima sesion planificada
                "ID Sesion": "SES-AL-NOREALIZ",
                "ID PACIENTE": "PAT-AL-003",
                "Paciente": "Perez, Carlos",
                "Tratamiento": "Alineadores",
                "Fecha de Sesion": future.strftime("%m/%d/%Y"),
                "Estado de Sesion": "Planificada",
            }],
            [],  # No hay sesiones realizadas
        ])

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today):

            result = await process_aligner_reminders()

        assert result["sent"] == 0
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_aligner_duplicate_prevention(self, db_session):
        """Ya enviado → skip."""
        today = date(2026, 3, 15)
        last_realized_date = today - timedelta(days=15)
        next_planned_date = today + timedelta(days=15)

        # Pre-insertar recordatorio ya enviado
        existing = SentReminder(
            reminder_type=ReminderType.ALIGNER_CHANGE,
            reference_id="SES-AL-DUP-LAST_day15",
            phone="1123266671",
            attempt=1,
            status=ReminderStatus.SENT,
        )
        db_session.add(existing)
        await db_session.flush()

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(side_effect=[
            [{
                "ID Sesion": "SES-AL-DUP-NEXT",
                "ID PACIENTE": "PAT-AL-DUP",
                "Paciente": "Garcia, Juan",
                "Tratamiento": "Alineadores",
                "Fecha de Sesion": next_planned_date.strftime("%m/%d/%Y"),
                "Estado de Sesion": "Planificada",
                "Telefono (Whatsapp)": "+5491123266671",
            }],
            [{
                "ID Sesion": "SES-AL-DUP-LAST",
                "ID PACIENTE": "PAT-AL-DUP",
                "Paciente": "Garcia, Juan",
                "Tratamiento": "Alineadores",
                "Fecha de Sesion": last_realized_date.strftime("%m/%d/%Y"),
                "Estado de Sesion": "Realizada",
            }],
        ])

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today), \
             patch("src.db.session.get_session_factory", return_value=mock_factory):

            result = await process_aligner_reminders()

        assert result["sent"] == 0
        assert result["skipped"] == 1


# =========================================================================
# FLUJO COMPLETO: REVIEW GOOGLE MAPS
# =========================================================================

class TestGoogleReviewFlow:
    """Tests del flujo de solicitud de review en Google Maps."""

    @pytest.mark.asyncio
    async def test_sends_review_after_realized_session(self, db_session):
        """Sesion realizada ayer → envia solicitud de review."""
        today = date(2026, 3, 15)
        yesterday = today - timedelta(days=1)

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Sesion": "SES-RV-001",
            "ID PACIENTE": "PAT-RV-001",
            "Paciente": "Garcia, Juan",
            "Fecha de Sesion": yesterday.strftime("%m/%d/%Y"),
            "Estado de Sesion": "Realizada",
            "Telefono (Whatsapp)": "+5491123266671",
        }])

        mock_send = AsyncMock(return_value={"status": "ok", "wa_message_id": "wamid.rv1"})

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_settings = MagicMock()
        mock_settings.google_maps_review_link = "https://g.page/r/CXyr_5_Wv5_7EBM/review"

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today), \
             patch("src.services.reminder_service.to_appsheet_date") as mock_to_date, \
             patch("src.services.reminder_service.get_settings", return_value=mock_settings), \
             patch("src.db.session.get_session_factory", return_value=mock_factory), \
             patch("src.services.proactive_message.send_text", mock_send):

            mock_to_date.return_value = yesterday.strftime("%m/%d/%Y")

            result = await process_google_review_requests()

        assert result["sent"] == 1

        stmt = select(SentReminder).where(SentReminder.reference_id == "SES-RV-001")
        db_result = await db_session.execute(stmt)
        reminder = db_result.scalar_one_or_none()
        assert reminder is not None
        assert reminder.reminder_type == ReminderType.GOOGLE_REVIEW_REQUEST
        assert "Google" in reminder.message_sent
        assert "g.page" in reminder.message_sent

    @pytest.mark.asyncio
    async def test_skips_if_no_review_link_configured(self):
        """Sin link de Google Maps → no enviar."""
        mock_settings = MagicMock()
        mock_settings.google_maps_review_link = ""

        with patch("src.services.reminder_service.get_settings", return_value=mock_settings):
            result = await process_google_review_requests()

        assert result["sent"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_skips_already_sent_review(self, db_session):
        """Review ya enviado → skip."""
        today = date(2026, 3, 15)
        yesterday = today - timedelta(days=1)

        # Pre-insertar review ya enviado
        existing = SentReminder(
            reminder_type=ReminderType.GOOGLE_REVIEW_REQUEST,
            reference_id="SES-RV-002",
            phone="1123266671",
            attempt=1,
            status=ReminderStatus.SENT,
        )
        db_session.add(existing)
        await db_session.flush()

        mock_appsheet = AsyncMock()
        mock_appsheet.find = AsyncMock(return_value=[{
            "ID Sesion": "SES-RV-002",
            "ID PACIENTE": "PAT-RV-002",
            "Paciente": "Garcia, Juan",
            "Fecha de Sesion": yesterday.strftime("%m/%d/%Y"),
            "Estado de Sesion": "Realizada",
            "Telefono (Whatsapp)": "+5491123266671",
        }])

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_settings = MagicMock()
        mock_settings.google_maps_review_link = "https://g.page/test"

        with patch("src.services.reminder_service.get_appsheet_client", return_value=mock_appsheet), \
             patch("src.services.reminder_service.today_argentina", return_value=today), \
             patch("src.services.reminder_service.to_appsheet_date") as mock_to_date, \
             patch("src.services.reminder_service.get_settings", return_value=mock_settings), \
             patch("src.db.session.get_session_factory", return_value=mock_factory):

            mock_to_date.return_value = yesterday.strftime("%m/%d/%Y")

            result = await process_google_review_requests()

        assert result["sent"] == 0
        assert result["skipped"] == 1

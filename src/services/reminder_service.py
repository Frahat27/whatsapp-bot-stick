"""
Servicio de recordatorios — logica core para recordatorios de turno y seguimiento de leads.

Llamado por scheduler.py. Cada funcion publica crea sus propias sesiones de DB.

Prevencion de duplicados: 3 capas
1. Pre-check SELECT en sent_reminders (rapido, evita trabajo innecesario)
2. UNIQUE constraint en PostgreSQL (imposible de violar, catch IntegrityError)
3. Redis distributed lock en scheduler.py (evita ejecucion concurrente)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db.clinic_repository import ClinicRepository
from src.db.clinic_session import get_clinic_session_factory
from src.models.conversation import Conversation, ContactType
from src.models.message import Message, MessageRole
from src.models.sent_reminder import ReminderType, ReminderStatus, SentReminder
from src.services.proactive_message import send_proactive_message
from src.utils.dates import from_appsheet_date, from_appsheet_time, today_argentina
from src.utils.logging_config import get_logger
from src.utils.phone import normalize_phone

logger = get_logger(__name__)

# Nombres de dias y meses en español para formatear mensajes
_DAYS_ES = {
    0: "lunes", 1: "martes", 2: "miercoles", 3: "jueves",
    4: "viernes", 5: "sabado", 6: "domingo",
}
_MONTHS_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


# =========================================================================
# RECORDATORIOS DE TURNO
# =========================================================================

async def process_appointment_reminders() -> dict:
    """
    Punto de entrada para recordatorios de turno.
    Busca sesiones de mañana con Estado="Planificada" y envia recordatorios.

    Returns:
        dict con contadores: sent, skipped, errors
    """
    from src.db.session import get_session_factory

    logger.info("appointment_reminders_started")

    tomorrow = today_argentina() + timedelta(days=1)

    # 1. Query Cloud SQL para sesiones de mañana "Planificada"
    clinic_factory = get_clinic_session_factory()
    try:
        async with clinic_factory() as clinic_db:
            repo = ClinicRepository(clinic_db)
            sessions_models = await repo.find_sessions_by_date_and_status(tomorrow, "Planificada")
            sessions = [s.to_appsheet_dict() for s in sessions_models]
    except Exception as e:
        logger.error("appointment_reminders_db_error", error=str(e))
        return {"sent": 0, "skipped": 0, "errors": 1}

    if not sessions:
        logger.info("appointment_reminders_no_sessions", date=str(tomorrow))
        return {"sent": 0, "skipped": 0, "errors": 0}

    logger.info("appointment_reminders_found", count=len(sessions), date=str(tomorrow))

    # 2. Procesar cada sesion
    sent_count = 0
    skip_count = 0
    error_count = 0

    factory = get_session_factory()

    for session_data in sessions:
        async with factory() as db:
            try:
                result = await _process_single_appointment_reminder(
                    db, session_data, tomorrow,
                )
                if result == "sent":
                    sent_count += 1
                elif result == "skipped":
                    skip_count += 1
                else:
                    error_count += 1
                await db.commit()
            except Exception as e:
                logger.error(
                    "appointment_reminder_error",
                    session_id=session_data.get("ID Sesion", "?"),
                    error=str(e),
                )
                await db.rollback()
                error_count += 1

    logger.info(
        "appointment_reminders_completed",
        sent=sent_count,
        skipped=skip_count,
        errors=error_count,
    )
    return {"sent": sent_count, "skipped": skip_count, "errors": error_count}


async def _process_single_appointment_reminder(
    db: AsyncSession,
    session_data: dict,
    appointment_date: date,
) -> str:
    """
    Procesar una sesion individual. Retorna "sent", "skipped", o "error".
    """
    session_id = session_data.get("ID Sesion", "")
    patient_id = session_data.get("ID PACIENTE", "")
    patient_name = session_data.get("Paciente", "")
    hora = session_data.get("Hora Sesion", "")
    profesional = session_data.get("Profesional Asignado", "")

    if not session_id or not patient_id:
        logger.warning("appointment_reminder_missing_data", session=session_data)
        return "error"

    # Capa 1: Pre-check — ¿ya enviamos este recordatorio?
    already_sent = await _check_already_sent(
        db, ReminderType.APPOINTMENT_24H, session_id, attempt=1,
    )
    if already_sent:
        logger.debug("appointment_reminder_already_sent", session_id=session_id)
        return "skipped"

    # Resolver telefono del paciente
    phone_10 = await _resolve_patient_phone(db, patient_id, session_data)
    if not phone_10:
        logger.warning(
            "appointment_reminder_no_phone",
            session_id=session_id,
            patient_id=patient_id,
        )
        return "error"

    # Formatear mensaje
    message = _format_appointment_message(
        patient_name, appointment_date, hora, profesional,
    )

    # Capa 2: INSERT ANTES de enviar (claim the slot)
    reminder = SentReminder(
        reminder_type=ReminderType.APPOINTMENT_24H,
        reference_id=session_id,
        phone=phone_10,
        attempt=1,
        status=ReminderStatus.SENT,
        message_sent=message,
        target_date=appointment_date,
    )
    db.add(reminder)

    try:
        await db.flush()  # UNIQUE constraint previene duplicados
    except IntegrityError:
        await db.rollback()
        logger.info("appointment_reminder_duplicate_caught", session_id=session_id)
        return "skipped"

    # Enviar via WhatsApp + guardar en historial de conversacion
    result = await send_proactive_message(
        db=db,
        phone_10=phone_10,
        text=message,
        patient_name=patient_name,
        patient_id=patient_id,
    )

    if result.get("status") != "ok":
        reminder.status = ReminderStatus.FAILED
        reminder.error_detail = str(result.get("error", ""))[:500]
        return "error"

    return "sent"


# =========================================================================
# SEGUIMIENTO DE LEADS
# =========================================================================

async def process_lead_followups() -> dict:
    """
    Punto de entrada para seguimiento de leads.
    Dia 3: leads "Nuevo" → primer seguimiento.
    Dia 7: leads "Contactado Frio" → segundo seguimiento.

    Returns:
        dict con contadores: sent, skipped, errors
    """
    from src.db.session import get_session_factory

    logger.info("lead_followup_started")

    today = today_argentina()
    day3_target = today - timedelta(days=3)
    day7_target = today - timedelta(days=7)

    # Query Cloud SQL para leads
    clinic_factory = get_clinic_session_factory()
    day3_leads = []
    day7_leads = []

    try:
        async with clinic_factory() as clinic_db:
            repo = ClinicRepository(clinic_db)
            day3_models = await repo.find_leads_by_status_and_date("Nuevo", day3_target)
            day3_leads = [l.to_appsheet_dict() for l in day3_models]
    except Exception as e:
        logger.error("lead_followup_day3_error", error=str(e))

    try:
        async with clinic_factory() as clinic_db:
            repo = ClinicRepository(clinic_db)
            day7_models = await repo.find_leads_by_status_and_date("Contactado Frio", day7_target)
            day7_leads = [l.to_appsheet_dict() for l in day7_models]
    except Exception as e:
        logger.error("lead_followup_day7_error", error=str(e))

    logger.info(
        "lead_followup_found",
        day3_count=len(day3_leads),
        day7_count=len(day7_leads),
    )

    factory = get_session_factory()
    sent = 0
    skipped = 0
    errors = 0

    # Procesar leads dia 3
    for lead in day3_leads:
        async with factory() as db:
            try:
                r = await _process_single_lead_followup(
                    db, lead, attempt=1,
                    reminder_type=ReminderType.LEAD_FOLLOWUP_DAY3,
                    new_lead_status="Contactado Frio",
                )
                if r == "sent":
                    sent += 1
                elif r == "skipped":
                    skipped += 1
                else:
                    errors += 1
                await db.commit()
            except Exception as e:
                logger.error("lead_followup_error", lead_id=lead.get("ID Lead"), error=str(e))
                await db.rollback()
                errors += 1

    # Procesar leads dia 7
    for lead in day7_leads:
        async with factory() as db:
            try:
                r = await _process_single_lead_followup(
                    db, lead, attempt=2,
                    reminder_type=ReminderType.LEAD_FOLLOWUP_DAY7,
                    new_lead_status="Cerrada Perdida",
                )
                if r == "sent":
                    sent += 1
                elif r == "skipped":
                    skipped += 1
                else:
                    errors += 1
                await db.commit()
            except Exception as e:
                logger.error("lead_followup_error", lead_id=lead.get("ID Lead"), error=str(e))
                await db.rollback()
                errors += 1

    logger.info(
        "lead_followup_completed",
        sent=sent,
        skipped=skipped,
        errors=errors,
    )
    return {"sent": sent, "skipped": skipped, "errors": errors}


async def _process_single_lead_followup(
    db: AsyncSession,
    lead: dict,
    attempt: int,
    reminder_type: ReminderType,
    new_lead_status: str,
) -> str:
    """Procesar un lead individual. Retorna 'sent', 'skipped', o 'error'."""
    lead_id = lead.get("ID Lead", "")
    lead_name = lead.get("Apellido y Nombre", "")
    lead_phone_raw = lead.get("Telefono (Whatsapp)", "")

    if not lead_id or not lead_phone_raw:
        logger.warning("lead_followup_missing_data", lead=lead)
        return "error"

    phone_10 = normalize_phone(lead_phone_raw)

    # Capa 1: Pre-check
    already_sent = await _check_already_sent(db, reminder_type, lead_id, attempt)
    if already_sent:
        logger.debug("lead_followup_already_sent", lead_id=lead_id, attempt=attempt)
        return "skipped"

    # Check si el lead respondio (tiene mensajes USER en la conversacion)
    has_responded = await _check_lead_responded(db, phone_10)
    if has_responded:
        logger.info(
            "lead_followup_skipped_responded",
            lead_id=lead_id,
            phone=phone_10,
        )
        # Registrar como CANCELLED para no reintentar
        cancelled = SentReminder(
            reminder_type=reminder_type,
            reference_id=lead_id,
            phone=phone_10,
            attempt=attempt,
            status=ReminderStatus.CANCELLED,
            message_sent="Lead respondio, follow-up cancelado",
        )
        db.add(cancelled)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
        return "skipped"

    # Formatear mensaje
    message = _format_lead_followup_message(lead_name, attempt)

    # Capa 2: INSERT antes de enviar
    reminder = SentReminder(
        reminder_type=reminder_type,
        reference_id=lead_id,
        phone=phone_10,
        attempt=attempt,
        status=ReminderStatus.SENT,
        message_sent=message,
        target_date=today_argentina(),
    )
    db.add(reminder)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.info("lead_followup_duplicate_caught", lead_id=lead_id, attempt=attempt)
        return "skipped"

    # Enviar
    result = await send_proactive_message(
        db=db,
        phone_10=phone_10,
        text=message,
        patient_name=lead_name,
        contact_type=ContactType.LEAD,
    )

    if result.get("status") != "ok":
        reminder.status = ReminderStatus.FAILED
        reminder.error_detail = str(result.get("error", ""))[:500]

    # Actualizar estado del lead en Cloud SQL
    clinic_factory = get_clinic_session_factory()
    try:
        async with clinic_factory() as clinic_db:
            repo = ClinicRepository(clinic_db)
            await repo.update_lead_status(lead_id, new_lead_status)
            await clinic_db.commit()
    except Exception as e:
        logger.error("lead_followup_db_update_error", lead_id=lead_id, error=str(e))

    return "sent" if result.get("status") == "ok" else "error"


# =========================================================================
# HELPERS COMPARTIDOS
# =========================================================================

async def _check_already_sent(
    db: AsyncSession,
    reminder_type: ReminderType,
    reference_id: str,
    attempt: int,
) -> bool:
    """Verificar si este recordatorio ya fue enviado o intentado."""
    stmt = select(SentReminder.id).where(
        SentReminder.reminder_type == reminder_type,
        SentReminder.reference_id == reference_id,
        SentReminder.attempt == attempt,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _resolve_patient_phone(
    db: AsyncSession,
    patient_id: str,
    session_data: dict,
) -> Optional[str]:
    """
    Resolver telefono del paciente, optimizando para minimizar queries.

    Estrategia:
    1. Ver si session_data ya trae el telefono
    2. Buscar en tabla conversations local (0 API calls)
    3. Fallback: query Cloud SQL BBDD PACIENTES (~5ms)
    """
    # Estrategia 1: telefono en los datos de la sesion
    phone_raw = session_data.get("Telefono (Whatsapp)", "")
    if phone_raw:
        return normalize_phone(phone_raw)

    # Estrategia 2: DB local (rapido)
    stmt = select(Conversation.phone).where(Conversation.patient_id == patient_id)
    result = await db.execute(stmt)
    local_phone = result.scalar_one_or_none()
    if local_phone:
        return local_phone

    # Estrategia 3: Cloud SQL (rapido ~5ms)
    try:
        clinic_factory = get_clinic_session_factory()
        async with clinic_factory() as clinic_db:
            repo = ClinicRepository(clinic_db)
            paciente = await repo.find_patient_by_id(patient_id)
            if paciente and paciente.telefono:
                return normalize_phone(paciente.telefono)
    except Exception as e:
        logger.error("resolve_phone_db_error", patient_id=patient_id, error=str(e))

    return None


async def _check_lead_responded(db: AsyncSession, phone_10: str) -> bool:
    """
    Verificar si un lead envio algun mensaje USER despues de creada la conversacion.
    Si respondio, el follow-up se cancela (el lead esta engaged).
    """
    stmt = (
        select(Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.phone == phone_10,
            Message.role == MessageRole.USER,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


def _format_appointment_message(
    name: str,
    appointment_date: date,
    hora: str,
    profesional: str,
) -> str:
    """Formatear mensaje de recordatorio usando template del system prompt 3E."""
    # Extraer primer nombre de formato "Apellido, Nombre"
    first_name = name.split(",")[-1].strip() if "," in name else name.strip()
    if not first_name:
        first_name = "paciente"

    # Formatear fecha: "miercoles 04 de marzo"
    day_name = _DAYS_ES.get(appointment_date.weekday(), "")
    month_name = _MONTHS_ES.get(appointment_date.month, "")
    date_str = f"{day_name} {appointment_date.day:02d} de {month_name}"

    # Formatear hora: "9:00" de "09:00:00"
    time_obj = from_appsheet_time(hora)
    if time_obj:
        hour_str = f"{time_obj.hour}:{time_obj.minute:02d}"
    else:
        hour_str = hora

    # Formatear profesional: "Hatzerian, Cynthia" → "Dra. Cynthia"
    prof_display = _format_professional_name(profesional)

    return (
        f"Hola {first_name} \U0001f60a Te escribo para recordarte que "
        f"ma\u00f1ana **{date_str}** ten\u00e9s turno a las **{hour_str}** "
        f"con **{prof_display}**. \u00bfConfirm\u00e1s que ven\u00eds?\n\n"
        f"Respond\u00e9 con **SI** para confirmar o **NO** para cancelar el turno."
    )


def _format_lead_followup_message(name: str, attempt: int) -> str:
    """Formatear mensaje de seguimiento de lead."""
    first_name = name.split(",")[-1].strip() if "," in name else name.strip()
    if not first_name:
        first_name = ""

    if attempt == 1:
        # Dia 3: primer seguimiento
        greeting = f"Hola {first_name} " if first_name else "Hola "
        return (
            f"{greeting}\U0001f60a \u00bfPudiste pensar lo que charlamos? "
            f"Si ten\u00e9s alguna duda m\u00e1s, ac\u00e1 estoy para ayudarte"
        )
    else:
        # Dia 7: segundo y ultimo seguimiento
        return (
            f"Hola, soy Sofia de Stick. Tenemos turnos disponibles esta semana. "
            f"\u00bfTe interesa que te reserve uno?"
        )


def _format_professional_name(profesional: str) -> str:
    """'Hatzerian, Cynthia' → 'Dra. Cynthia', 'Miño, Ana' → 'Dra. Ana'."""
    if not profesional:
        return "el profesional"
    parts = profesional.split(",")
    if len(parts) >= 2:
        first = parts[1].strip()
        return f"Dra. {first}"
    return profesional


# =========================================================================
# CONFIRMACIÓN DE TURNO (enviado al agendar el turno)
# =========================================================================

async def process_appointment_confirmations() -> dict:
    """
    Punto de entrada para confirmaciones de turno.
    Busca sesiones futuras con Estado="Planificada" que NO tengan
    APPOINTMENT_CONFIRMATION en sent_reminders. Envia confirmacion.

    Returns:
        dict con contadores: sent, skipped, errors
    """
    from src.db.session import get_session_factory

    logger.info("appointment_confirmations_started")

    today = today_argentina()

    # Query Cloud SQL para sesiones "Planificada" futuras
    clinic_factory = get_clinic_session_factory()
    try:
        async with clinic_factory() as clinic_db:
            repo = ClinicRepository(clinic_db)
            sessions_models = await repo.find_planned_future_sessions(today)
            sessions = [s.to_appsheet_dict() for s in sessions_models]
    except Exception as e:
        logger.error("appointment_confirmations_db_error", error=str(e))
        return {"sent": 0, "skipped": 0, "errors": 1}

    if not sessions:
        logger.info("appointment_confirmations_no_sessions")
        return {"sent": 0, "skipped": 0, "errors": 0}

    # Todas las sesiones ya son futuras (filtrado en SQL)
    future_sessions = sessions

    logger.info(
        "appointment_confirmations_found",
        total=len(sessions),
        future=len(future_sessions),
    )

    factory = get_session_factory()
    sent = 0
    skipped = 0
    errors = 0

    for session_data in future_sessions:
        async with factory() as db:
            try:
                result = await _process_single_confirmation(db, session_data)
                if result == "sent":
                    sent += 1
                elif result == "skipped":
                    skipped += 1
                else:
                    errors += 1
                await db.commit()
            except Exception as e:
                logger.error(
                    "appointment_confirmation_error",
                    session_id=session_data.get("ID Sesion", "?"),
                    error=str(e),
                )
                await db.rollback()
                errors += 1

    logger.info(
        "appointment_confirmations_completed",
        sent=sent,
        skipped=skipped,
        errors=errors,
    )
    return {"sent": sent, "skipped": skipped, "errors": errors}


async def _process_single_confirmation(
    db: AsyncSession,
    session_data: dict,
) -> str:
    """Procesar confirmacion de una sesion individual."""
    session_id = session_data.get("ID Sesion", "")
    patient_id = session_data.get("ID PACIENTE", "")
    patient_name = session_data.get("Paciente", "")
    hora = session_data.get("Hora Sesion", "")
    profesional = session_data.get("Profesional Asignado", "")
    fecha_str = session_data.get("Fecha de Sesion", "")

    if not session_id or not patient_id:
        logger.warning("appointment_confirmation_missing_data", session=session_data)
        return "error"

    # Capa 1: Pre-check
    already_sent = await _check_already_sent(
        db, ReminderType.APPOINTMENT_CONFIRMATION, session_id, attempt=1,
    )
    if already_sent:
        return "skipped"

    # Resolver telefono
    phone_10 = await _resolve_patient_phone(db, patient_id, session_data)
    if not phone_10:
        logger.warning(
            "appointment_confirmation_no_phone",
            session_id=session_id,
            patient_id=patient_id,
        )
        return "error"

    # Parsear fecha
    appointment_date = from_appsheet_date(fecha_str)
    if not appointment_date:
        logger.warning("appointment_confirmation_bad_date", fecha=fecha_str)
        return "error"

    # Formatear mensaje
    message = _format_confirmation_message(
        patient_name, appointment_date, hora, profesional,
    )

    # Capa 2: INSERT antes de enviar
    reminder = SentReminder(
        reminder_type=ReminderType.APPOINTMENT_CONFIRMATION,
        reference_id=session_id,
        phone=phone_10,
        attempt=1,
        status=ReminderStatus.SENT,
        message_sent=message,
        target_date=appointment_date,
    )
    db.add(reminder)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.info("appointment_confirmation_duplicate", session_id=session_id)
        return "skipped"

    # Enviar
    result = await send_proactive_message(
        db=db,
        phone_10=phone_10,
        text=message,
        patient_name=patient_name,
        patient_id=patient_id,
    )

    if result.get("status") != "ok":
        reminder.status = ReminderStatus.FAILED
        reminder.error_detail = str(result.get("error", ""))[:500]
        return "error"

    return "sent"


def _format_confirmation_message(
    name: str,
    appointment_date: date,
    hora: str,
    profesional: str,
) -> str:
    """Formatear mensaje de confirmacion de turno agendado."""
    first_name = name.split(",")[-1].strip() if "," in name else name.strip()
    if not first_name:
        first_name = "paciente"

    day_name = _DAYS_ES.get(appointment_date.weekday(), "")
    month_name = _MONTHS_ES.get(appointment_date.month, "")
    date_str = f"{day_name} {appointment_date.day:02d} de {month_name}"

    time_obj = from_appsheet_time(hora)
    if time_obj:
        hour_str = f"{time_obj.hour}:{time_obj.minute:02d}"
    else:
        hour_str = hora

    prof_display = _format_professional_name(profesional)

    return (
        f"Hola {first_name} \U0001f60a Tu turno qued\u00f3 agendado para el "
        f"**{date_str}** a las **{hour_str}** con **{prof_display}** "
        f"en **Virrey del Pino 4191 3C, Belgrano**.\n\n"
        f"Un d\u00eda antes te escribo para confirmarlo \U0001f60a"
    )


# =========================================================================
# SALUDO DE CUMPLEAÑOS
# =========================================================================

async def process_birthday_greetings() -> dict:
    """
    Punto de entrada para saludos de cumpleaños.
    Busca pacientes activos cuyo cumpleaños es hoy.

    Returns:
        dict con contadores: sent, skipped, errors
    """
    from src.db.session import get_session_factory

    logger.info("birthday_greetings_started")

    today = today_argentina()

    # Query Cloud SQL para pacientes activos con cumpleaños hoy (filtrado en SQL)
    clinic_factory = get_clinic_session_factory()
    try:
        async with clinic_factory() as clinic_db:
            repo = ClinicRepository(clinic_db)
            birthday_models = await repo.find_active_patients_with_birthday(
                today.month, today.day,
            )
            birthday_patients = [p.to_appsheet_dict() for p in birthday_models]
    except Exception as e:
        logger.error("birthday_greetings_db_error", error=str(e))
        return {"sent": 0, "skipped": 0, "errors": 1}

    logger.info(
        "birthday_greetings_found",
        birthdays_today=len(birthday_patients),
    )

    if not birthday_patients:
        return {"sent": 0, "skipped": 0, "errors": 0}

    factory = get_session_factory()
    sent = 0
    skipped = 0
    errors = 0

    for patient in birthday_patients:
        async with factory() as db:
            try:
                result = await _process_single_birthday(db, patient, today)
                if result == "sent":
                    sent += 1
                elif result == "skipped":
                    skipped += 1
                else:
                    errors += 1
                await db.commit()
            except Exception as e:
                logger.error(
                    "birthday_greeting_error",
                    patient_id=patient.get("ID Paciente", "?"),
                    error=str(e),
                )
                await db.rollback()
                errors += 1

    logger.info(
        "birthday_greetings_completed",
        sent=sent,
        skipped=skipped,
        errors=errors,
    )
    return {"sent": sent, "skipped": skipped, "errors": errors}


async def _process_single_birthday(
    db: AsyncSession,
    patient: dict,
    today: date,
) -> str:
    """Procesar saludo de cumpleaños de un paciente."""
    patient_id = patient.get("ID Paciente", "")
    patient_name = patient.get("Paciente", "")
    phone_raw = patient.get("Telefono (Whatsapp)", "")

    if not patient_id or not phone_raw:
        logger.warning("birthday_greeting_missing_data", patient=patient)
        return "error"

    phone_10 = normalize_phone(phone_raw)

    # reference_id incluye año para prevenir duplicados anuales
    reference_id = f"{patient_id}_{today.year}"

    # Capa 1: Pre-check
    already_sent = await _check_already_sent(
        db, ReminderType.BIRTHDAY_GREETING, reference_id, attempt=1,
    )
    if already_sent:
        return "skipped"

    # Formatear mensaje
    message = _format_birthday_message(patient_name)

    # Capa 2: INSERT antes de enviar
    reminder = SentReminder(
        reminder_type=ReminderType.BIRTHDAY_GREETING,
        reference_id=reference_id,
        phone=phone_10,
        attempt=1,
        status=ReminderStatus.SENT,
        message_sent=message,
        target_date=today,
    )
    db.add(reminder)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.info("birthday_greeting_duplicate", patient_id=patient_id)
        return "skipped"

    # Enviar
    result = await send_proactive_message(
        db=db,
        phone_10=phone_10,
        text=message,
        patient_name=patient_name,
        patient_id=patient_id,
    )

    if result.get("status") != "ok":
        reminder.status = ReminderStatus.FAILED
        reminder.error_detail = str(result.get("error", ""))[:500]
        return "error"

    return "sent"


def _format_birthday_message(name: str) -> str:
    """Formatear mensaje de saludo de cumpleaños."""
    first_name = name.split(",")[-1].strip() if "," in name else name.strip()
    if not first_name:
        first_name = "paciente"

    return (
        f"Hola {first_name} \U0001f60a \u00a1Feliz cumplea\u00f1os! "
        f"Te deseamos un hermoso d\u00eda de parte de todo el equipo de STICK. "
        f"\u00a1Que la pases genial! \U0001f382"
    )


# =========================================================================
# RECORDATORIO DE CAMBIO DE ALINEADORES
# =========================================================================

async def process_aligner_reminders() -> dict:
    """
    Punto de entrada para recordatorios de cambio de alineadores.
    Busca pacientes con sesiones futuras de Alineadores en BBDD SESIONES
    y calcula si hoy toca enviar recordatorio segun el ciclo.

    Returns:
        dict con contadores: sent, skipped, errors
    """
    from src.db.session import get_session_factory

    logger.info("aligner_reminders_started")

    today = today_argentina()
    clinic_factory = get_clinic_session_factory()

    # Buscar sesiones futuras de Alineadores (Planificada o Confirmada)
    # Esto identifica pacientes con tratamiento activo
    try:
        async with clinic_factory() as clinic_db:
            repo = ClinicRepository(clinic_db)
            next_sessions_models = await repo.find_aligner_sessions_active()
            next_sessions = [s.to_appsheet_dict() for s in next_sessions_models]
    except Exception as e:
        logger.error("aligner_reminders_db_error", error=str(e))
        return {"sent": 0, "skipped": 0, "errors": 1}

    if not next_sessions:
        logger.info("aligner_reminders_no_active_patients")
        return {"sent": 0, "skipped": 0, "errors": 0}

    # Agrupar por paciente (tomar la sesion mas proxima por paciente)
    patient_next_session = {}
    for s in next_sessions:
        pid = s.get("ID PACIENTE", "")
        if not pid:
            continue
        session_date = from_appsheet_date(s.get("Fecha de Sesion", ""))
        if not session_date or session_date < today:
            continue
        # Guardar la sesion mas proxima
        if pid not in patient_next_session or session_date < from_appsheet_date(
            patient_next_session[pid].get("Fecha de Sesion", "")
        ):
            patient_next_session[pid] = s

    logger.info(
        "aligner_reminders_patients_found",
        patients_count=len(patient_next_session),
    )

    # Para cada paciente, buscar su ultima sesion Realizada de Alineadores
    factory = get_session_factory()
    sent = 0
    skipped = 0
    errors = 0

    for patient_id, next_session in patient_next_session.items():
        # Buscar ultima sesion Realizada de Alineadores
        try:
            async with clinic_factory() as clinic_db:
                repo = ClinicRepository(clinic_db)
                realized_models = await repo.find_aligner_sessions_realized(patient_id)
                realized_sessions = [s.to_appsheet_dict() for s in realized_models]
        except Exception as e:
            logger.error(
                "aligner_reminder_realized_error",
                patient_id=patient_id,
                error=str(e),
            )
            errors += 1
            continue

        if not realized_sessions:
            # Sin sesiones realizadas, no hay ciclo que calcular
            logger.debug(
                "aligner_reminder_no_realized",
                patient_id=patient_id,
            )
            skipped += 1
            continue

        # Encontrar la sesion realizada mas reciente
        last_realized = _find_most_recent_session(realized_sessions)
        if not last_realized:
            skipped += 1
            continue

        async with factory() as db:
            try:
                result = await _process_single_aligner_reminder(
                    db, patient_id, last_realized, next_session, today,
                )
                if result == "sent":
                    sent += 1
                elif result == "skipped":
                    skipped += 1
                else:
                    errors += 1
                await db.commit()
            except Exception as e:
                logger.error(
                    "aligner_reminder_error",
                    patient_id=patient_id,
                    error=str(e),
                )
                await db.rollback()
                errors += 1

    logger.info(
        "aligner_reminders_completed",
        sent=sent,
        skipped=skipped,
        errors=errors,
    )
    return {"sent": sent, "skipped": skipped, "errors": errors}


def _find_most_recent_session(sessions: list[dict]) -> Optional[dict]:
    """Encontrar la sesion con fecha mas reciente."""
    best = None
    best_date = None
    for s in sessions:
        d = from_appsheet_date(s.get("Fecha de Sesion", ""))
        if d and (best_date is None or d > best_date):
            best = s
            best_date = d
    return best


def _get_aligner_reminder_days(cycle_days: int) -> list[int]:
    """
    Dado los dias del ciclo (entre ultima Realizada y proxima Planificada),
    retorna los dias desde la ultima sesion en que se debe enviar recordatorio.

    Logica del system prompt seccion 3F:
    - 22-26 dias (ciclo corto): enviar a los 12 dias
    - 27-34 dias (ciclo estandar): enviar a los 15 dias
    - 34+ dias (ciclo largo): enviar a los 15 y 30 dias
    """
    if cycle_days < 22:
        return []  # Ciclo muy corto, no enviar
    elif cycle_days <= 26:
        return [12]
    elif cycle_days <= 34:
        return [15]
    else:
        return [15, 30]


async def _process_single_aligner_reminder(
    db: AsyncSession,
    patient_id: str,
    last_realized: dict,
    next_session: dict,
    today: date,
) -> str:
    """Procesar recordatorio de cambio de alineadores para un paciente."""
    last_date = from_appsheet_date(last_realized.get("Fecha de Sesion", ""))
    next_date = from_appsheet_date(next_session.get("Fecha de Sesion", ""))
    patient_name = next_session.get("Paciente", "") or last_realized.get("Paciente", "")
    last_session_id = last_realized.get("ID Sesion", "")

    if not last_date or not next_date or not last_session_id:
        return "error"

    # Calcular ciclo
    cycle_days = (next_date - last_date).days
    reminder_days = _get_aligner_reminder_days(cycle_days)

    if not reminder_days:
        return "skipped"

    # Calcular dias transcurridos desde ultima sesion realizada
    days_since_last = (today - last_date).days

    # Verificar si hoy coincide con algun dia de envio
    matching_day = None
    for day in reminder_days:
        if days_since_last == day:
            matching_day = day
            break

    if matching_day is None:
        return "skipped"

    # reference_id unico por ciclo: {last_session_id}_day{X}
    reference_id = f"{last_session_id}_day{matching_day}"

    # Capa 1: Pre-check
    already_sent = await _check_already_sent(
        db, ReminderType.ALIGNER_CHANGE, reference_id, attempt=1,
    )
    if already_sent:
        return "skipped"

    # Resolver telefono
    phone_10 = await _resolve_patient_phone(db, patient_id, next_session)
    if not phone_10:
        logger.warning(
            "aligner_reminder_no_phone",
            patient_id=patient_id,
        )
        return "error"

    # Formatear mensaje
    message = _format_aligner_message(patient_name)

    # Capa 2: INSERT antes de enviar
    reminder = SentReminder(
        reminder_type=ReminderType.ALIGNER_CHANGE,
        reference_id=reference_id,
        phone=phone_10,
        attempt=1,
        status=ReminderStatus.SENT,
        message_sent=message,
        target_date=today,
    )
    db.add(reminder)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.info("aligner_reminder_duplicate", reference_id=reference_id)
        return "skipped"

    # Enviar
    result = await send_proactive_message(
        db=db,
        phone_10=phone_10,
        text=message,
        patient_name=patient_name,
        patient_id=patient_id,
    )

    if result.get("status") != "ok":
        reminder.status = ReminderStatus.FAILED
        reminder.error_detail = str(result.get("error", ""))[:500]
        return "error"

    return "sent"


def _format_aligner_message(name: str) -> str:
    """Formatear mensaje de recordatorio de cambio de alineadores."""
    first_name = name.split(",")[-1].strip() if "," in name else name.strip()
    if not first_name:
        first_name = "paciente"

    return (
        f"Hola {first_name} \U0001f60a Te recuerdo que ya es momento de cambiar "
        f"al siguiente juego de alineadores. Record\u00e1 usarlos entre 20 y 22 "
        f"horas por d\u00eda para que el tratamiento avance bien. "
        f"\u00bfTodo bien con las placas?"
    )


# =========================================================================
# SOLICITUD DE REVIEW EN GOOGLE MAPS
# =========================================================================

async def process_google_review_requests() -> dict:
    """
    Punto de entrada para solicitudes de review en Google Maps.
    Busca sesiones realizadas ayer y envia solicitud de review.

    Returns:
        dict con contadores: sent, skipped, errors
    """
    from src.db.session import get_session_factory

    settings = get_settings()

    if not settings.google_maps_review_link:
        logger.info("google_review_skipped_no_link")
        return {"sent": 0, "skipped": 0, "errors": 0}

    logger.info("google_review_requests_started")

    yesterday = today_argentina() - timedelta(days=1)

    clinic_factory = get_clinic_session_factory()
    try:
        async with clinic_factory() as clinic_db:
            repo = ClinicRepository(clinic_db)
            sessions_models = await repo.find_sessions_by_date_and_status(
                yesterday, "Realizada",
            )
            sessions = [s.to_appsheet_dict() for s in sessions_models]
    except Exception as e:
        logger.error("google_review_db_error", error=str(e))
        return {"sent": 0, "skipped": 0, "errors": 1}

    if not sessions:
        logger.info("google_review_no_sessions", date=str(yesterday))
        return {"sent": 0, "skipped": 0, "errors": 0}

    logger.info("google_review_sessions_found", count=len(sessions))

    factory = get_session_factory()
    sent = 0
    skipped = 0
    errors = 0

    for session_data in sessions:
        async with factory() as db:
            try:
                result = await _process_single_review_request(
                    db, session_data, settings.google_maps_review_link,
                )
                if result == "sent":
                    sent += 1
                elif result == "skipped":
                    skipped += 1
                else:
                    errors += 1
                await db.commit()
            except Exception as e:
                logger.error(
                    "google_review_error",
                    session_id=session_data.get("ID Sesion", "?"),
                    error=str(e),
                )
                await db.rollback()
                errors += 1

    logger.info(
        "google_review_requests_completed",
        sent=sent,
        skipped=skipped,
        errors=errors,
    )
    return {"sent": sent, "skipped": skipped, "errors": errors}


async def _process_single_review_request(
    db: AsyncSession,
    session_data: dict,
    review_link: str,
) -> str:
    """Procesar solicitud de review para una sesion."""
    session_id = session_data.get("ID Sesion", "")
    patient_id = session_data.get("ID PACIENTE", "")
    patient_name = session_data.get("Paciente", "")

    if not session_id or not patient_id:
        logger.warning("google_review_missing_data", session=session_data)
        return "error"

    # Capa 1: Pre-check
    already_sent = await _check_already_sent(
        db, ReminderType.GOOGLE_REVIEW_REQUEST, session_id, attempt=1,
    )
    if already_sent:
        return "skipped"

    # Resolver telefono
    phone_10 = await _resolve_patient_phone(db, patient_id, session_data)
    if not phone_10:
        logger.warning(
            "google_review_no_phone",
            session_id=session_id,
            patient_id=patient_id,
        )
        return "error"

    # Formatear mensaje
    message = _format_review_message(patient_name, review_link)

    # Capa 2: INSERT antes de enviar
    reminder = SentReminder(
        reminder_type=ReminderType.GOOGLE_REVIEW_REQUEST,
        reference_id=session_id,
        phone=phone_10,
        attempt=1,
        status=ReminderStatus.SENT,
        message_sent=message,
        target_date=today_argentina() - timedelta(days=1),
    )
    db.add(reminder)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.info("google_review_duplicate", session_id=session_id)
        return "skipped"

    # Enviar
    result = await send_proactive_message(
        db=db,
        phone_10=phone_10,
        text=message,
        patient_name=patient_name,
        patient_id=patient_id,
    )

    if result.get("status") != "ok":
        reminder.status = ReminderStatus.FAILED
        reminder.error_detail = str(result.get("error", ""))[:500]
        return "error"

    return "sent"


def _format_review_message(name: str, review_link: str) -> str:
    """Formatear mensaje de solicitud de review en Google Maps."""
    first_name = name.split(",")[-1].strip() if "," in name else name.strip()
    if not first_name:
        first_name = "paciente"

    return (
        f"Hola {first_name} \U0001f60a Esperamos que tu visita de ayer haya sido "
        f"una buena experiencia. Si ten\u00e9s un minutito, nos ayudar\u00eda "
        f"mucho que nos dejes tu opini\u00f3n en Google: {review_link}\n\n"
        f"\u00a1Gracias! \U0001f64f"
    )


# =========================================================================
# ALERTA ADMIN: PACIENTES EN CURSO SIN PROXIMO TURNO
# =========================================================================

async def process_en_curso_sin_turno_alerts() -> dict:
    """
    Detecta pacientes con tratamiento EN CURSO en BBDD ALINEADORES
    que no tienen ningun turno planificado/confirmado en BBDD SESIONES.
    Envia alerta al primer admin configurado.

    Returns:
        dict con contadores: alerted, skipped, errors
    """
    from src.db.session import get_session_factory

    logger.info("en_curso_sin_turno_started")

    settings = get_settings()
    admin_phones = settings.admin_phone_list
    if not admin_phones:
        logger.warning("en_curso_sin_turno_no_admin_phones")
        return {"alerted": 0, "skipped": 0, "errors": 0}

    clinic_factory = get_clinic_session_factory()

    # 1. Buscar pacientes con alineadores EN CURSO
    try:
        async with clinic_factory() as clinic_db:
            repo = ClinicRepository(clinic_db)
            en_curso = await repo.find_aligners_en_curso()
    except Exception as e:
        logger.error("en_curso_sin_turno_db_error", error=str(e))
        return {"alerted": 0, "skipped": 0, "errors": 1}

    if not en_curso:
        logger.info("en_curso_sin_turno_none_found")
        return {"alerted": 0, "skipped": 0, "errors": 0}

    logger.info("en_curso_found", count=len(en_curso))

    # 2. Para cada uno, verificar si tiene turno futuro
    patients_sin_turno = []
    today = today_argentina()

    for alineador in en_curso:
        patient_id = alineador.id_paciente
        if not patient_id:
            continue

        try:
            async with clinic_factory() as clinic_db:
                repo = ClinicRepository(clinic_db)
                active_sessions = await repo.find_patient_active_sessions(patient_id)
                # Filtrar solo futuras
                future_sessions = [
                    s for s in active_sessions
                    if s.fecha and s.fecha >= today
                ]
        except Exception as e:
            logger.error(
                "en_curso_session_check_error",
                patient_id=patient_id,
                error=str(e),
            )
            continue

        if not future_sessions:
            patients_sin_turno.append(alineador)

    if not patients_sin_turno:
        logger.info("en_curso_sin_turno_all_have_appointments")
        return {"alerted": 0, "skipped": len(en_curso), "errors": 0}

    # 3. Construir mensaje de alerta y enviar al admin
    factory = get_session_factory()
    admin_phone = admin_phones[0]  # Franco

    lines = [
        f"⚠️ *Alerta: {len(patients_sin_turno)} paciente(s) EN CURSO sin turno*\n",
    ]
    for a in patients_sin_turno:
        name = a.paciente or "Sin nombre"
        tipo = a.tipo_tratamiento or "Alineadores"
        lines.append(f"• *{name}* — {tipo} (ID: {a.id_paciente})")

    lines.append(
        "\nEstos pacientes tienen tratamiento activo pero no tienen "
        "próximo turno planificado. Considerar contactar para agendar."
    )

    message = "\n".join(lines)

    # Check dedup: solo alertar una vez por día
    today_str = today.isoformat()
    dedup_ref = f"en_curso_sin_turno_{today_str}"

    async with factory() as db:
        already_sent = await _check_already_sent(
            db, ReminderType.APPOINTMENT_REMINDER, dedup_ref, attempt=99,
        )
        if already_sent:
            logger.info("en_curso_sin_turno_already_alerted_today")
            return {"alerted": 0, "skipped": len(patients_sin_turno), "errors": 0}

        # Registrar envio
        reminder = SentReminder(
            reminder_type=ReminderType.APPOINTMENT_REMINDER,
            reference_id=dedup_ref,
            phone=admin_phone,
            attempt=99,  # Distinguir de recordatorios normales
            status=ReminderStatus.SENT,
            message_sent=message[:500],
            target_date=today,
        )
        db.add(reminder)

        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            return {"alerted": 0, "skipped": len(patients_sin_turno), "errors": 0}

        # Enviar
        result = await send_proactive_message(
            db=db,
            phone_10=admin_phone,
            text=message,
            patient_name="Admin Alert",
            contact_type=ContactType.ADMIN,
        )

        if result.get("status") != "ok":
            reminder.status = ReminderStatus.FAILED
            reminder.error_detail = str(result.get("error", ""))[:500]
            await db.commit()
            logger.error("en_curso_sin_turno_send_failed", error=result.get("error"))
            return {"alerted": 0, "skipped": 0, "errors": 1}

        await db.commit()

    logger.info(
        "en_curso_sin_turno_alert_sent",
        patients=len(patients_sin_turno),
        admin_phone=admin_phone,
    )
    return {"alerted": len(patients_sin_turno), "skipped": 0, "errors": 0}


# =========================================================================
# CONSULTAS SIN RESPUESTA (>24h)
# =========================================================================

async def process_unanswered_queries() -> dict:
    """
    Detecta conversaciones bot_active donde el ultimo mensaje fue del paciente
    hace mas de 24h sin respuesta del bot. Alerta al admin.

    Esto cubre casos donde el bot falló silenciosamente (error, timeout, etc.)
    y el paciente quedó sin respuesta.

    Returns:
        dict con contadores: alerted, skipped, errors
    """
    from sqlalchemy import func, and_, or_
    from src.db.session import get_session_factory
    from src.models.conversation_state import ConversationState, ConversationStatus
    from src.utils.dates import now_argentina

    logger.info("unanswered_queries_started")

    settings = get_settings()
    admin_phones = settings.admin_phone_list
    if not admin_phones:
        return {"alerted": 0, "skipped": 0, "errors": 0}

    cutoff = now_argentina() - timedelta(hours=24)
    factory = get_session_factory()

    try:
        async with factory() as db:
            # Buscar conversaciones bot_active donde el ultimo mensaje fue del user
            # y fue hace mas de 24h
            last_msg_subq = (
                select(
                    Message.conversation_id,
                    func.max(Message.id).label("last_msg_id"),
                )
                .group_by(Message.conversation_id)
                .subquery()
            )

            query = (
                select(
                    Conversation.id,
                    Conversation.phone,
                    Conversation.patient_name,
                    Message.content,
                    Message.created_at,
                )
                .join(last_msg_subq, Conversation.id == last_msg_subq.c.conversation_id)
                .join(Message, Message.id == last_msg_subq.c.last_msg_id)
                .outerjoin(ConversationState, ConversationState.conversation_id == Conversation.id)
                .where(
                    and_(
                        Conversation.is_active == True,
                        or_(
                            ConversationState.status == ConversationStatus.BOT_ACTIVE,
                            ConversationState.status == None,
                        ),
                        Message.role == MessageRole.USER,
                        Message.created_at < cutoff,
                    ),
                )
            )

            result = await db.execute(query)
            unanswered = result.all()

    except Exception as e:
        logger.error("unanswered_queries_db_error", error=str(e))
        return {"alerted": 0, "skipped": 0, "errors": 1}

    if not unanswered:
        logger.info("unanswered_queries_none")
        return {"alerted": 0, "skipped": 0, "errors": 0}

    # Dedup: solo alertar una vez por día
    today_str = today_argentina().isoformat()
    dedup_ref = f"unanswered_queries_{today_str}"

    async with factory() as db:
        already_sent = await _check_already_sent(
            db, ReminderType.APPOINTMENT_REMINDER, dedup_ref, attempt=98,
        )
        if already_sent:
            logger.info("unanswered_queries_already_alerted_today")
            return {"alerted": 0, "skipped": len(unanswered), "errors": 0}

        # Construir mensaje
        lines = [
            f"⚠️ *{len(unanswered)} consulta(s) sin respuesta (>24h)*\n",
        ]
        for conv_id, phone, name, content, created_at in unanswered[:10]:
            preview = (content[:60] + "...") if content and len(content) > 60 else (content or "")
            lines.append(f"• *{name or phone}*: \"{preview}\"")

        if len(unanswered) > 10:
            lines.append(f"\n... y {len(unanswered) - 10} más")

        lines.append("\nRevisá en el panel admin.")
        message = "\n".join(lines)

        # Registrar dedup
        reminder = SentReminder(
            reminder_type=ReminderType.APPOINTMENT_REMINDER,
            reference_id=dedup_ref,
            phone=admin_phones[0],
            attempt=98,
            status=ReminderStatus.SENT,
            message_sent=message[:500],
            target_date=today_argentina(),
        )
        db.add(reminder)

        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            return {"alerted": 0, "skipped": len(unanswered), "errors": 0}

        # Enviar al admin
        result = await send_proactive_message(
            db=db,
            phone_10=admin_phones[0],
            text=message,
            patient_name="Admin Alert",
            contact_type=ContactType.ADMIN,
        )

        if result.get("status") != "ok":
            reminder.status = ReminderStatus.FAILED
            reminder.error_detail = str(result.get("error", ""))[:500]

        await db.commit()

    logger.info("unanswered_queries_alert_sent", count=len(unanswered))
    return {"alerted": len(unanswered), "skipped": 0, "errors": 0}

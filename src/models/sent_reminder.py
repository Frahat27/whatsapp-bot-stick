"""
Modelo: sent_reminders — registro de recordatorios enviados.

Tabla de deduplicacion: NUNCA enviar el mismo recordatorio dos veces
para la misma persona y el mismo evento.

La UNIQUE constraint (reminder_type, reference_id, attempt) es la
garantia absoluta contra duplicados a nivel de base de datos.
"""

from __future__ import annotations

import enum
from datetime import date
from typing import Optional

from sqlalchemy import BigInteger, Date, Enum, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class ReminderType(str, enum.Enum):
    """Tipo de recordatorio."""
    APPOINTMENT_24H = "appointment_24h"
    LEAD_FOLLOWUP_DAY3 = "lead_followup_day3"
    LEAD_FOLLOWUP_DAY7 = "lead_followup_day7"
    APPOINTMENT_CONFIRMATION = "appointment_confirmation"
    BIRTHDAY_GREETING = "birthday_greeting"
    ALIGNER_CHANGE = "aligner_change"
    GOOGLE_REVIEW_REQUEST = "google_review_request"


class ReminderStatus(str, enum.Enum):
    """Estado del envio."""
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"  # Lead respondio antes del follow-up


class SentReminder(TimestampMixin, Base):
    """
    Registro de cada recordatorio enviado.

    La UNIQUE constraint es la garantia absoluta contra duplicados:
    - Para appointment_24h: reference_id = session_id de AppSheet
    - Para lead_followup: reference_id = lead_id de AppSheet
    - attempt: 1 para turnos, 1 (dia 3) o 2 (dia 7) para leads
    """

    __tablename__ = "sent_reminders"

    __table_args__ = (
        UniqueConstraint(
            "reminder_type", "reference_id", "attempt",
            name="uq_reminder_type_ref_attempt",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Que tipo de recordatorio
    reminder_type: Mapped[ReminderType] = mapped_column(
        Enum(ReminderType), nullable=False, index=True
    )

    # ID externo: session_id para turnos, lead_id para follow-ups
    reference_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Telefono destino (normalizado 10 digitos)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Numero de intento (1 para turnos, 1 o 2 para leads)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Resultado del envio
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus), default=ReminderStatus.SENT, nullable=False
    )

    # Texto exacto enviado (auditoria)
    message_sent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Fecha objetivo (fecha del turno, o fecha del follow-up)
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Detalle de error si status=FAILED
    error_detail: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<SentReminder(type={self.reminder_type}, ref={self.reference_id}, "
            f"phone={self.phone}, attempt={self.attempt}, status={self.status})>"
        )

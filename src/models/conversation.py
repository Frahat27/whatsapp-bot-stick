"""
Modelo: conversations — una conversación por teléfono.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Enum, String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class ContactType(str, enum.Enum):
    """Tipo de contacto identificado."""
    PACIENTE = "paciente"
    LEAD = "lead"
    NUEVO = "nuevo"
    ADMIN = "admin"


class Conversation(TimestampMixin, Base):
    """
    Una conversación por teléfono.
    Contiene el contexto de quién es el contacto y su estado.
    """

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Identificación del contacto
    contact_type: Mapped[ContactType] = mapped_column(
        Enum(ContactType), default=ContactType.NUEVO, nullable=False
    )
    patient_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    patient_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    lead_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Estado
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relaciones
    messages: Mapped[list["Message"]] = relationship(  # noqa: F821
        back_populates="conversation",
        order_by="Message.created_at",
        lazy="selectin",
    )
    state: Mapped[Optional["ConversationState"]] = relationship(  # noqa: F821
        back_populates="conversation",
        uselist=False,
        lazy="selectin",
    )
    summaries: Mapped[list["ConversationSummary"]] = relationship(  # noqa: F821
        back_populates="conversation",
        order_by="ConversationSummary.created_at",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, phone={self.phone}, type={self.contact_type})>"

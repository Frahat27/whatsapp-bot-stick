"""
Modelo: conversation_states — estado de escalado y flujo de cada conversación.
Modelo: conversation_summaries — memoria de largo plazo.
"""

import enum
from typing import Optional

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class ConversationStatus(str, enum.Enum):
    """Estado de control de la conversación."""
    BOT_ACTIVE = "bot_active"          # Sofía maneja la conversación
    ESCALATED = "escalated"            # Escalada a humano, esperando takeover
    ADMIN_TAKEOVER = "admin_takeover"  # Humano tiene el control


class ConversationState(TimestampMixin, Base):
    """
    Estado de escalado y metadata de una conversación.
    1:1 con Conversation.
    """

    __tablename__ = "conversation_states"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )

    # Estado actual
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.BOT_ACTIVE, nullable=False
    )

    # Labels (para filtros en panel admin)
    labels: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), default=list, nullable=True
    )

    # Contexto del flujo actual (flexible JSONB)
    flow_context: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=dict, nullable=True
    )

    # Notas internas (admin)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relación
    conversation: Mapped["Conversation"] = relationship(back_populates="state")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ConversationState(conv_id={self.conversation_id}, status={self.status})>"


class ConversationSummary(TimestampMixin, Base):
    """
    Resúmenes comprimidos de conversaciones (memoria largo plazo).
    Generados por Claude cuando una conversación supera N mensajes.
    """

    __tablename__ = "conversation_summaries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Resumen generado por Claude
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Rango de mensajes que cubre
    message_id_start: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id_end: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relación
    conversation: Mapped["Conversation"] = relationship(back_populates="summaries")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ConversationSummary(conv_id={self.conversation_id}, msgs={self.message_count})>"

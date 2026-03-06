"""
Modelo: messages — historial completo de mensajes.
"""

import enum
from typing import Optional

from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class MessageRole(str, enum.Enum):
    """Quién envió el mensaje."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, enum.Enum):
    """Tipo de contenido del mensaje."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    DOCUMENT = "document"
    LOCATION = "location"
    STICKER = "sticker"
    REACTION = "reaction"


class Message(TimestampMixin, Base):
    """
    Un mensaje individual en una conversación.
    Almacena tanto mensajes del usuario como respuestas de Sofía.
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Contenido
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType), default=MessageType.TEXT, nullable=False
    )

    # WhatsApp dedup
    wa_message_id: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, nullable=True, index=True
    )

    # Media (para imágenes, audio, docs)
    media_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relación
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")  # noqa: F821

    def __repr__(self) -> str:
        preview = self.content[:50] if self.content else ""
        return f"<Message(id={self.id}, role={self.role}, preview='{preview}...')>"

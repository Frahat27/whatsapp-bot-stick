"""
Modelo: tool_calls — registro de tool calls ejecutadas por Claude.
Permite al panel admin ver qué herramientas usó Sofía en cada conversación.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import BigInteger, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class ToolCall(TimestampMixin, Base):
    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tool_input: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    tool_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)

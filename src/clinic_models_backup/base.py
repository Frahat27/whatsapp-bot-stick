"""
Base declarativa y mixins para modelos de Cloud SQL (clinic data).
Separados de src/models/base.py que es para Neon (bot-internal).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ClinicBase(DeclarativeBase):
    """Base declarativa para modelos de Cloud SQL (clinic data)."""

    def to_dict(self) -> dict[str, Any]:
        """Convertir modelo a dict con nombres de columna SQL."""
        result = {}
        for col in self.__table__.columns:
            val = getattr(self, col.key)
            if isinstance(val, datetime):
                val = val.isoformat()
            elif hasattr(val, "isoformat"):
                val = val.isoformat()
            result[col.key] = val
        return result

    def to_appsheet_dict(self) -> dict[str, Any]:
        """
        Convertir modelo a dict con los nombres EXACTOS de AppSheet.
        Override en cada modelo para mapear attribute_name -> "AppSheet Column Name".
        Por defecto retorna to_dict() (nombres SQL = nombres AppSheet).
        """
        return self.to_dict()


class ClinicTimestampMixin:
    """Mixin que agrega created_at y updated_at (idéntico a bot-internal)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

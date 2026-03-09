"""Modelo EstadoSesion — mapea config."LISTA J | Estado de Sesion" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class EstadoSesion(ClinicBase):
    """Estado posible de una sesion."""

    __tablename__ = "LISTA J | Estado de Sesion"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    id_status_sesion: Mapped[Optional[int]] = mapped_column(
        "ID Status Sesion", Integer
    )
    status_sesion: Mapped[Optional[str]] = mapped_column(
        "Status Sesion", Text
    )

    def __repr__(self) -> str:
        return f"<EstadoSesion {self.row_id} {self.status_sesion}>"

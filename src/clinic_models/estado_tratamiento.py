"""Modelo EstadoTratamiento — mapea config."LISTA I | Estado de Tratamiento" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class EstadoTratamiento(ClinicBase):
    """Estado posible de un tratamiento."""

    __tablename__ = "LISTA I | Estado de Tratamiento"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    id_status_trat: Mapped[Optional[int]] = mapped_column(
        "ID Status Trat", Integer
    )
    status_tratamiento: Mapped[Optional[str]] = mapped_column(
        "Status Tratamiento", Text
    )

    def __repr__(self) -> str:
        return f"<EstadoTratamiento {self.row_id} {self.status_tratamiento}>"

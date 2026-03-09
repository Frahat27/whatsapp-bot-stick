"""Modelo UnidadNegocio — mapea config."LISTA N | UNIDAD DE NEGOCIO" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class UnidadNegocio(ClinicBase):
    """Unidad de negocio (STICK, STICK PRO, etc.)."""

    __tablename__ = "LISTA N | UNIDAD DE NEGOCIO"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    unidad_negocio: Mapped[Optional[str]] = mapped_column(
        "Unidad de negocio", Text
    )

    def __repr__(self) -> str:
        return f"<UnidadNegocio {self.row_id} {self.unidad_negocio}>"

"""Modelo UnidadMedida — mapea config."LISTA H | Unidad de medida" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class UnidadMedida(ClinicBase):
    """Unidad de medida para insumos."""

    __tablename__ = "LISTA H | Unidad de medida"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    id_unidad: Mapped[Optional[int]] = mapped_column(
        "ID Unidad", Integer
    )
    unidad_medida: Mapped[Optional[str]] = mapped_column(
        "Unidad medida", Text
    )

    def __repr__(self) -> str:
        return f"<UnidadMedida {self.row_id} {self.unidad_medida}>"

"""Modelo TipoGasto — mapea config."LISTA F | TIPO DE GASTO" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class TipoGasto(ClinicBase):
    """Categoria y detalle de gasto."""

    __tablename__ = "LISTA F | TIPO DE GASTO"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[Optional[str]] = mapped_column("Row ID", Text)
    id_tipo_gasto: Mapped[int] = mapped_column(
        "ID TIPO GASTO", Integer, primary_key=True
    )
    tipo_gasto: Mapped[str] = mapped_column(
        "TIPO DE GASTO", Text, nullable=False
    )
    detalle: Mapped[str] = mapped_column(
        "Detalle", Text, nullable=False
    )
    unidad: Mapped[Optional[str]] = mapped_column(
        "Unidad", Text
    )

    def __repr__(self) -> str:
        return f"<TipoGasto {self.id_tipo_gasto} {self.tipo_gasto} {self.detalle}>"

"""Modelo TipoEncuesta — mapea config."LISTA E | TIPO DE ENCUESTA" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class TipoEncuesta(ClinicBase):
    """Tipo de encuesta de satisfaccion."""

    __tablename__ = "LISTA E | TIPO DE ENCUESTA"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[Optional[str]] = mapped_column("Row ID", Text)
    id_encuesta: Mapped[int] = mapped_column(
        "ID Encuesta", Integer, primary_key=True
    )
    tipo_encuesta: Mapped[Optional[str]] = mapped_column(
        "Tipo de Encuesta", Text
    )

    def __repr__(self) -> str:
        return f"<TipoEncuesta {self.id_encuesta} {self.tipo_encuesta}>"

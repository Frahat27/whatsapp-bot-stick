"""Modelo FuenteCaptacion — mapea config."LISTA B | FUENTE CAPTACION" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class FuenteCaptacion(ClinicBase):
    """Fuente de captacion de leads/pacientes."""

    __tablename__ = "LISTA B | FUENTE CAPTACION"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[Optional[str]] = mapped_column("Row ID", Text)
    id_fuente: Mapped[int] = mapped_column(
        "ID Fuente", Integer, primary_key=True
    )
    fuente_captacion: Mapped[Optional[str]] = mapped_column(
        "Fuente Captacion", Text
    )
    status_fuente: Mapped[Optional[str]] = mapped_column(
        "Status Fuente", Text
    )

    def __repr__(self) -> str:
        return f"<FuenteCaptacion {self.id_fuente} {self.fuente_captacion}>"

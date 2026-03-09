"""Modelo MetodoPago — mapea config."LISTA G | Metodo de Pago" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class MetodoPago(ClinicBase):
    """Metodo de pago aceptado."""

    __tablename__ = "LISTA G | Metodo de Pago"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[Optional[str]] = mapped_column("Row ID", Text)
    id_metodo_pago: Mapped[int] = mapped_column(
        "ID Metodo Pago", Integer, primary_key=True
    )
    metodo_pago: Mapped[Optional[str]] = mapped_column(
        "Metodo de Pago", Text
    )

    def __repr__(self) -> str:
        return f"<MetodoPago {self.id_metodo_pago} {self.metodo_pago}>"

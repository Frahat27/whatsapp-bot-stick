"""Modelo EstadoPago — mapea config."LISTA G1 | Estado de Pago" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class EstadoPago(ClinicBase):
    """Estado posible de un pago."""

    __tablename__ = "LISTA G1 | Estado de Pago"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    id_status_pago: Mapped[Optional[int]] = mapped_column(
        "ID Status Pago", Integer
    )
    status_pago: Mapped[Optional[str]] = mapped_column(
        "Status pago", Text
    )

    def __repr__(self) -> str:
        return f"<EstadoPago {self.row_id} {self.status_pago}>"

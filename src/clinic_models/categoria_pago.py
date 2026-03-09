"""Modelo CategoriaPago — mapea config."LISTA M | CATEGORIA DE PAGOS" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class CategoriaPago(ClinicBase):
    """Categoria/tipo de pago (Sena, Arancel, Cuota, etc.)."""

    __tablename__ = "LISTA M | CATEGORIA DE PAGOS"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    tipo_pago: Mapped[Optional[str]] = mapped_column(
        "Tipo de Pago", Text
    )

    def __repr__(self) -> str:
        return f"<CategoriaPago {self.row_id} {self.tipo_pago}>"

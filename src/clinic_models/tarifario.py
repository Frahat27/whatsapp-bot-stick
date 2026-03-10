"""Modelo Tarifario — mapea operacional."BBDD TARIFARIO" en Cloud SQL."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Tarifario(ClinicBase):
    """Precio de un tratamiento."""

    __tablename__ = "BBDD TARIFARIO"
    __table_args__ = {"schema": "operacional"}

    tratamiento: Mapped[str] = mapped_column(
        "Tratamiento", String(200), primary_key=True
    )
    tratamiento_detalle: Mapped[Optional[str]] = mapped_column(
        "Tratamiento Detalle", String(200)
    )
    precio_lista: Mapped[Optional[Decimal]] = mapped_column(
        "Precio Lista", Numeric(12, 2)
    )
    precio_efectivo: Mapped[Optional[Decimal]] = mapped_column(
        "Precio Efectivo", Numeric(12, 2)
    )
    moneda: Mapped[Optional[str]] = mapped_column(
        "Moneda", String(20), default="PESOS"
    )
    sena: Mapped[Optional[Decimal]] = mapped_column(
        "Seña", Numeric(12, 2)
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet."""
        return {
            "Tratamiento": self.tratamiento,
            "Tratamiento Detalle": self.tratamiento_detalle,
            "Precio Lista": (
                float(self.precio_lista) if self.precio_lista else None
            ),
            "Precio Efectivo": (
                float(self.precio_efectivo) if self.precio_efectivo else None
            ),
            "Moneda": self.moneda,
            "Seña": float(self.sena) if self.sena else None,
        }

    def __repr__(self) -> str:
        return f"<Tarifario {self.tratamiento} ${self.precio_lista}>"

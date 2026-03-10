"""Modelo Tarifario — mapea operacional."BBDD TARIFARIO" en Cloud SQL."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Tarifario(ClinicBase):
    """Precio de un tratamiento.

    NOTA: La estructura real de la tabla en Cloud SQL puede diferir del DDL
    original. El handler de consultar_tarifario tiene un fallback a raw SQL
    que funciona sin importar las columnas reales.

    PK original (DDL): "Tratamiento" solo.
    PK real (segun MEMORY): composite ("Tratamiento", "Tratamiento Detalle").
    """

    __tablename__ = "BBDD TARIFARIO"
    __table_args__ = {"schema": "operacional"}

    # Composite PK segun alteracion post-DDL
    tratamiento: Mapped[str] = mapped_column(
        "Tratamiento", String(200), primary_key=True
    )
    tratamiento_detalle: Mapped[str] = mapped_column(
        "Tratamiento Detalle", String(200), primary_key=True
    )
    precio_lista: Mapped[Optional[Decimal]] = mapped_column(
        "Precio Lista", Numeric(12, 2)
    )
    # AppSheet usa "Precio efectivo" (e minuscula) — respetamos ese casing
    precio_efectivo: Mapped[Optional[Decimal]] = mapped_column(
        "Precio efectivo", Numeric(12, 2)
    )
    moneda: Mapped[Optional[str]] = mapped_column(
        "Moneda", String(20), default="PESOS"
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet."""
        return {
            "Tratamiento": self.tratamiento,
            "Tratamiento Detalle": self.tratamiento_detalle,
            "Precio Lista": (
                float(self.precio_lista) if self.precio_lista else None
            ),
            "Precio efectivo": (
                float(self.precio_efectivo) if self.precio_efectivo else None
            ),
            "Moneda": self.moneda,
        }

    def __repr__(self) -> str:
        return f"<Tarifario {self.tratamiento} ${self.precio_lista}>"

"""Modelo Conciliacion — mapea operacional."BBDD CONCILIACION" en Cloud SQL."""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Date, Numeric, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Conciliacion(ClinicBase):
    """Cierre de caja diario."""

    __tablename__ = "BBDD CONCILIACION"
    __table_args__ = {"schema": "operacional"}

    id_cierre: Mapped[str] = mapped_column(
        "ID CIERRE", String(50), primary_key=True
    )
    fecha: Mapped[Optional[date]] = mapped_column(
        "Fecha", Date
    )
    responsable: Mapped[str] = mapped_column(
        "Responsable", String(200), nullable=False, default="Hatzerian, Cynthia"
    )
    hora_cierre: Mapped[Optional[time]] = mapped_column(
        "Hora de Cierre", Time
    )
    saldo_caja_inicio: Mapped[Optional[Decimal]] = mapped_column(
        "Saldo_Caja_Inicio", Numeric(12, 2), default=0
    )
    efectivo_contado_pesos: Mapped[Optional[Decimal]] = mapped_column(
        "Efectivo_Contado_PESOS", Numeric(12, 2)
    )
    transferencia_banco_pesos: Mapped[Optional[Decimal]] = mapped_column(
        "Transferencia_Banco_PESOS", Numeric(12, 2)
    )
    observaciones: Mapped[Optional[str]] = mapped_column(
        "Observaciones", Text
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet."""
        return {
            "ID CIERRE": self.id_cierre,
            "Fecha": self.fecha.isoformat() if self.fecha else None,
            "Responsable": self.responsable,
            "Hora de Cierre": (
                self.hora_cierre.strftime("%H:%M:%S")
                if self.hora_cierre else None
            ),
            "Saldo_Caja_Inicio": float(self.saldo_caja_inicio) if self.saldo_caja_inicio else None,
            "Efectivo_Contado_PESOS": float(self.efectivo_contado_pesos) if self.efectivo_contado_pesos else None,
            "Transferencia_Banco_PESOS": float(self.transferencia_banco_pesos) if self.transferencia_banco_pesos else None,
            "Observaciones": self.observaciones,
        }

    def __repr__(self) -> str:
        return f"<Conciliacion {self.id_cierre} {self.fecha}>"

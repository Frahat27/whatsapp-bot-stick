"""Modelo Presupuesto — mapea operacional."BBDD PRESUPUESTOS" en Cloud SQL."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Date, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Presupuesto(ClinicBase):
    """Presupuesto de tratamiento para un paciente."""

    __tablename__ = "BBDD PRESUPUESTOS"
    __table_args__ = {"schema": "operacional"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    id_presupuesto: Mapped[Optional[str]] = mapped_column(
        "ID Presupuesto", String(50)
    )
    id_paciente: Mapped[Optional[str]] = mapped_column(
        "ID Paciente", String(50),
    )
    paciente: Mapped[Optional[str]] = mapped_column(
        "Paciente", String(200)
    )
    telefono: Mapped[Optional[str]] = mapped_column(
        "Telefono", String(30)
    )
    tratamiento: Mapped[Optional[str]] = mapped_column(
        "Tratamiento", String(200)
    )
    descripcion: Mapped[Optional[str]] = mapped_column(
        "Descripción", Text
    )
    fecha_presupuesto: Mapped[Optional[date]] = mapped_column(
        "Fecha Presupuesto", Date, server_default="CURRENT_DATE"
    )
    monto_total: Mapped[Optional[Decimal]] = mapped_column(
        "Monto Total", Numeric(12, 2)
    )
    moneda: Mapped[Optional[str]] = mapped_column(
        "Moneda", String(20), default="PESOS"
    )
    estado: Mapped[Optional[str]] = mapped_column(
        "ESTADO", String(50), default="ACTIVO"
    )
    id_alineadores: Mapped[Optional[str]] = mapped_column(
        "ID Alineadores", String(50)
    )
    cuotas: Mapped[Optional[str]] = mapped_column(
        "Cuotas", Text
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet."""
        return {
            "Row ID": self.row_id,
            "ID Presupuesto": self.id_presupuesto,
            "ID Paciente": self.id_paciente,
            "Paciente": self.paciente,
            "Telefono": self.telefono,
            "Tratamiento": self.tratamiento,
            "Descripción": self.descripcion,
            "Fecha Presupuesto": (
                self.fecha_presupuesto.strftime("%m/%d/%Y")
                if self.fecha_presupuesto else None
            ),
            "Monto Total": float(self.monto_total) if self.monto_total else None,
            "Moneda": self.moneda,
            "ESTADO": self.estado,
            "ID Alineadores": self.id_alineadores,
            "Cuotas": self.cuotas,
        }

    def __repr__(self) -> str:
        return f"<Presupuesto {self.row_id} {self.paciente} {self.tratamiento}>"

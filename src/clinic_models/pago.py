"""Modelo Pago — mapea operacional."BBDD PAGOS" en Cloud SQL."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Pago(ClinicBase):
    """Pago registrado de un paciente."""

    __tablename__ = "BBDD PAGOS"
    __table_args__ = {"schema": "operacional"}

    id_pago: Mapped[str] = mapped_column(
        "ID Pago", String(50), primary_key=True
    )
    id_paciente: Mapped[Optional[str]] = mapped_column(
        "ID PACIENTE", String(50),
        ForeignKey('operacional."BBDD PACIENTES"."ID Paciente"'),
    )
    paciente: Mapped[Optional[str]] = mapped_column(
        "Paciente", String(200)
    )
    tratamiento: Mapped[Optional[str]] = mapped_column(
        "Tratamiento", String(200)
    )
    fecha: Mapped[Optional[date]] = mapped_column(
        "Fecha del Pago", Date
    )
    monto: Mapped[Optional[Decimal]] = mapped_column(
        "Monto Pagado", Numeric(12, 2)
    )
    moneda: Mapped[Optional[str]] = mapped_column(
        "Moneda", String(20), default="PESOS"
    )
    metodo: Mapped[Optional[str]] = mapped_column(
        "Metodo de Pago", String(50)
    )
    estado: Mapped[Optional[str]] = mapped_column(
        "Estado del Pago", String(50), default="Confirmado"
    )
    tipo: Mapped[Optional[str]] = mapped_column(
        "Tipo de Pago", String(50)
    )
    cuenta: Mapped[Optional[str]] = mapped_column(
        "CUENTA", String(50), default="CYNTHIA"
    )
    nro_operacion: Mapped[Optional[str]] = mapped_column(
        "Nro de Operacion", String(100)
    )
    quiere_factura: Mapped[Optional[bool]] = mapped_column(
        "Quiere Factura?", Boolean, default=False
    )
    observaciones: Mapped[Optional[str]] = mapped_column(
        "Observaciones", Text
    )
    tipo_paciente: Mapped[Optional[str]] = mapped_column(
        "Tipo de Paciente", String(50)
    )
    # Campos nuevos (futuro)
    consultorio: Mapped[Optional[str]] = mapped_column(
        "Consultorio", String(50), default="SALA 1"
    )
    sede: Mapped[Optional[str]] = mapped_column(
        "Sede", String(100), default="Virrey del Pino"
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet."""
        return {
            "ID Pago": self.id_pago,
            "ID PACIENTE": self.id_paciente,
            "Paciente": self.paciente,
            "Tratamiento": self.tratamiento,
            "Fecha del Pago": (
                self.fecha.strftime("%m/%d/%Y")
                if self.fecha else None
            ),
            "Monto Pagado": float(self.monto) if self.monto else None,
            "Moneda": self.moneda,
            "Metodo de Pago": self.metodo,
            "Estado del Pago": self.estado,
            "Tipo de Pago": self.tipo,
            "CUENTA": self.cuenta,
            "Nro de Operacion": self.nro_operacion,
            "Quiere Factura?": self.quiere_factura,
            "Observaciones": self.observaciones,
            "Tipo de Paciente": self.tipo_paciente,
            "Consultorio": self.consultorio,
            "Sede": self.sede,
        }

    def __repr__(self) -> str:
        return f"<Pago {self.id_pago} {self.paciente} ${self.monto}>"

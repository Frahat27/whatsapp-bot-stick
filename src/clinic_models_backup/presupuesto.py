"""Modelo Presupuesto — mapea operacional."BBDD PRESUPUESTOS" en Cloud SQL."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase, ClinicTimestampMixin


class Presupuesto(ClinicTimestampMixin, ClinicBase):
    """Presupuesto de tratamiento para un paciente."""

    __tablename__ = "BBDD PRESUPUESTOS"
    __table_args__ = {"schema": "operacional"}

    # AppSheet usa composite key (Row ID + ID Presupuesto)
    # En PostgreSQL usamos Row ID como PK
    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    id_presupuesto: Mapped[Optional[str]] = mapped_column(
        "ID Presupuesto", String(50)
    )
    id_paciente: Mapped[Optional[str]] = mapped_column(
        "ID Paciente", String(50),
        ForeignKey('operacional."BBDD PACIENTES"."ID Paciente"'),
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
    saldo_pendiente: Mapped[Optional[Decimal]] = mapped_column(
        "Saldo Pendiente", Numeric(12, 2)
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
            "Saldo Pendiente": (
                float(self.saldo_pendiente) if self.saldo_pendiente else None
            ),
        }

    def __repr__(self) -> str:
        return f"<Presupuesto {self.row_id} {self.paciente} {self.tratamiento}>"

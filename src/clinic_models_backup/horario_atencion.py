"""Modelo HorarioAtencion — mapea config."LISTA O | HORARIOS DE ATENCION" en Cloud SQL."""

from __future__ import annotations

from datetime import time
from typing import Any, Optional

from sqlalchemy import String, Time
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase, ClinicTimestampMixin


class HorarioAtencion(ClinicTimestampMixin, ClinicBase):
    """Horario de atencion de la clinica por dia."""

    __tablename__ = "LISTA O | HORARIOS DE ATENCION"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    dia: Mapped[str] = mapped_column(
        "DIA", String(20), nullable=False
    )
    hora_inicio: Mapped[Optional[time]] = mapped_column(
        "HORA INICIO", Time
    )
    hora_cierre: Mapped[Optional[time]] = mapped_column(
        "HORA CIERRE", Time
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet."""
        return {
            "Row ID": self.row_id,
            "DIA": self.dia,
            "HORA INICIO": (
                self.hora_inicio.strftime("%H:%M:%S")
                if self.hora_inicio else None
            ),
            "HORA CIERRE": (
                self.hora_cierre.strftime("%H:%M:%S")
                if self.hora_cierre else None
            ),
        }

    def __repr__(self) -> str:
        return f"<HorarioAtencion {self.dia} {self.hora_inicio}-{self.hora_cierre}>"

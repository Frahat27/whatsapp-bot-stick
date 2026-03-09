"""Modelo EstadoPaciente — mapea config."LISTA D | Estado Paciente" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class EstadoPaciente(ClinicBase):
    """Estado posible de un paciente."""

    __tablename__ = "LISTA D | Estado Paciente"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[Optional[str]] = mapped_column("Row ID", Text)
    id_status_paciente: Mapped[int] = mapped_column(
        "ID Status Paciente", Integer, primary_key=True
    )
    estado_paciente: Mapped[Optional[str]] = mapped_column(
        "Estado Paciente", Text
    )

    def __repr__(self) -> str:
        return f"<EstadoPaciente {self.id_status_paciente} {self.estado_paciente}>"

"""Modelo Nota — mapea operacional."BBDD NOTAS" en Cloud SQL."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Nota(ClinicBase):
    """Nota clinica de un paciente."""

    __tablename__ = "BBDD NOTAS"
    __table_args__ = {"schema": "operacional"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    id_paciente: Mapped[Optional[str]] = mapped_column(
        "ID Paciente", String(50),
        ForeignKey('operacional."BBDD PACIENTES"."ID Paciente"'),
    )
    paciente: Mapped[Optional[str]] = mapped_column(
        "Paciente", Text
    )
    tratamiento: Mapped[Optional[str]] = mapped_column(
        "Tratamiento", Text
    )
    comentario: Mapped[Optional[str]] = mapped_column(
        "Comentario", Text
    )
    fecha_nota: Mapped[Optional[date]] = mapped_column(
        "Fecha de Nota", Date
    )
    status: Mapped[Optional[str]] = mapped_column(
        "Status", Text, default="Pendiente"
    )

    def __repr__(self) -> str:
        return f"<Nota {self.row_id} {self.paciente}>"

"""Modelo Orden — mapea operacional."BBDD ORDENES" en Cloud SQL."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Orden(ClinicBase):
    """Orden medica de un paciente."""

    __tablename__ = "BBDD ORDENES"
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
    orden_necesaria: Mapped[Optional[str]] = mapped_column(
        "Orden necesaria", Text
    )
    fecha_creacion: Mapped[Optional[date]] = mapped_column(
        "Fecha creacion", Date
    )
    status: Mapped[Optional[str]] = mapped_column(
        "Status", Text, default="Pendiente"
    )
    dni: Mapped[Optional[int]] = mapped_column(
        "DNI", Numeric
    )
    obra_social: Mapped[Optional[str]] = mapped_column(
        "Obra Social", Text
    )

    def __repr__(self) -> str:
        return f"<Orden {self.row_id} {self.paciente}>"

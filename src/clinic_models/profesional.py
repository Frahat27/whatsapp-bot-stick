"""Modelo Profesional — mapea operacional."BBDD PROFESIONALES" en Cloud SQL."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Profesional(ClinicBase):
    """Profesional/empleado de la clinica."""

    __tablename__ = "BBDD PROFESIONALES"
    __table_args__ = {"schema": "operacional"}

    id_profesional: Mapped[int] = mapped_column(
        "ID Profesional", Integer, primary_key=True
    )
    profesional: Mapped[Optional[str]] = mapped_column(
        "Profesional", Text, default="APELLIDO, NOMBRE"
    )
    tipo: Mapped[Optional[str]] = mapped_column(
        "TIPO", Text
    )
    status: Mapped[Optional[str]] = mapped_column(
        "Status", Text, default="ACTIVADO"
    )
    fecha_inicio: Mapped[Optional[date]] = mapped_column(
        "Fecha inicio", Date
    )
    fecha_finalizacion: Mapped[Optional[date]] = mapped_column(
        "Fecha Finalizacion", Date
    )
    foto: Mapped[Optional[str]] = mapped_column(
        "FOTO", Text
    )

    def __repr__(self) -> str:
        return f"<Profesional {self.id_profesional} {self.profesional}>"

"""Modelo Sesion — mapea operacional."BBDD SESIONES" en Cloud SQL."""

from __future__ import annotations

from datetime import date, time, timedelta
from typing import Any, Optional

from sqlalchemy import Date, ForeignKey, Interval, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Sesion(ClinicBase):
    """Sesion/turno de un paciente."""

    __tablename__ = "BBDD SESIONES"
    __table_args__ = {"schema": "operacional"}

    id_sesion: Mapped[str] = mapped_column(
        "ID Sesion", String(50), primary_key=True
    )
    id_paciente: Mapped[Optional[str]] = mapped_column(
        "ID PACIENTE", String(50),
        ForeignKey('operacional."BBDD PACIENTES"."ID Paciente"'),
    )
    paciente: Mapped[str] = mapped_column(
        "Paciente", String(200), nullable=False
    )
    tratamiento: Mapped[Optional[str]] = mapped_column(
        "Tratamiento", String(200)
    )
    motivo_sesion: Mapped[Optional[str]] = mapped_column(
        "Motivo Sesion", String(200)
    )
    fecha: Mapped[Optional[date]] = mapped_column(
        "Fecha de Sesion", Date, index=True
    )
    hora: Mapped[Optional[time]] = mapped_column(
        "Hora Sesion", Time
    )
    hora_fin: Mapped[Optional[time]] = mapped_column(
        "Horario Finalizacion", Time
    )
    duracion: Mapped[Optional[timedelta]] = mapped_column(
        "Duracion", Interval
    )
    profesional: Mapped[Optional[str]] = mapped_column(
        "Profesional Asignado", String(200)
    )
    estado: Mapped[Optional[str]] = mapped_column(
        "Estado de Sesion", String(50), default="Planificada", index=True
    )
    descripcion: Mapped[Optional[str]] = mapped_column(
        "Descripcion de la sesion", Text
    )
    observaciones: Mapped[Optional[str]] = mapped_column(
        "Observaciones", Text
    )
    # NOTA: "Solapamiento turnos" (ord 14), "Telefono (Whatsapp)" (ord 16),
    # "Email" (ord 17) fueron eliminadas de la DB. NO incluir.
    fecha_creacion: Mapped[Optional[date]] = mapped_column(
        "Fecha Creacion", Date, server_default="CURRENT_DATE"
    )
    consultorio: Mapped[Optional[str]] = mapped_column(
        "Consultorio", String(50), default="SALA 1"
    )
    sede: Mapped[Optional[str]] = mapped_column(
        "Sede", String(100), default="Virrey del Pino"
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet."""
        return {
            "ID Sesion": self.id_sesion,
            "ID PACIENTE": self.id_paciente,
            "Paciente": self.paciente,
            "Tratamiento": self.tratamiento,
            "Motivo Sesion": self.motivo_sesion,
            "Fecha de Sesion": (
                self.fecha.strftime("%m/%d/%Y")
                if self.fecha else None
            ),
            "Hora Sesion": (
                self.hora.strftime("%H:%M")
                if self.hora else None
            ),
            "Horario Finalizacion": (
                self.hora_fin.strftime("%H:%M")
                if self.hora_fin else None
            ),
            "Duracion": (
                int(self.duracion.total_seconds() / 60)
                if self.duracion else None
            ),
            "Profesional Asignado": self.profesional,
            "Estado de Sesion": self.estado,
            "Descripcion de la sesion": self.descripcion,
            "Observaciones": self.observaciones,
            "Fecha Creacion": (
                self.fecha_creacion.strftime("%m/%d/%Y")
                if self.fecha_creacion else None
            ),
            "Consultorio": self.consultorio,
            "Sede": self.sede,
        }

    def __repr__(self) -> str:
        return f"<Sesion {self.id_sesion} {self.paciente} {self.fecha}>"

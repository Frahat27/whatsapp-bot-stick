"""Modelo Paciente — mapea operacional."BBDD PACIENTES" en Cloud SQL."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Paciente(ClinicBase):
    """Paciente registrado en la clinica."""

    __tablename__ = "BBDD PACIENTES"
    __table_args__ = {"schema": "operacional"}

    # Column names match AppSheet EXACTLY (double-quoted in PostgreSQL)
    id_paciente: Mapped[str] = mapped_column(
        "ID Paciente", String(50), primary_key=True
    )
    paciente: Mapped[str] = mapped_column(
        "Paciente", String(200), nullable=False
    )
    telefono: Mapped[Optional[str]] = mapped_column(
        "Telefono (Whatsapp)", String(30), index=True
    )
    email: Mapped[Optional[str]] = mapped_column(
        "email", String(200), default="1@1.com"
    )
    fecha_nacimiento: Mapped[Optional[date]] = mapped_column(
        "Fecha Nacimiento", Date
    )
    sexo: Mapped[Optional[str]] = mapped_column(
        "Sexo", String(20), default="Otro"
    )
    dni: Mapped[Optional[str]] = mapped_column(
        "DNI / Pasaporte", String(30), default="COMPLETAR"
    )
    estado: Mapped[Optional[str]] = mapped_column(
        "Estado del Paciente", String(50), default="Activo"
    )
    fecha_alta: Mapped[Optional[date]] = mapped_column(
        "Fecha de Alta", Date, server_default="CURRENT_DATE"
    )
    fuente_captacion: Mapped[Optional[str]] = mapped_column(
        "Fuente de Captacion", String(100)
    )
    referido: Mapped[Optional[str]] = mapped_column(
        "Referido", String(200)
    )
    notas: Mapped[Optional[str]] = mapped_column(
        "Notas", Text
    )
    consgen_firmado: Mapped[Optional[str]] = mapped_column(
        "CONSGEN FIRMADO", String(200), default=""
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet (para backward compat)."""
        d = {}
        d["ID Paciente"] = self.id_paciente
        d["Paciente"] = self.paciente
        d["Telefono (Whatsapp)"] = self.telefono
        d["email"] = self.email
        d["Fecha Nacimiento"] = (
            self.fecha_nacimiento.strftime("%m/%d/%Y")
            if self.fecha_nacimiento else None
        )
        d["Sexo"] = self.sexo
        d["DNI / Pasaporte"] = self.dni
        d["Estado del Paciente"] = self.estado
        d["Fecha de Alta"] = (
            self.fecha_alta.strftime("%m/%d/%Y")
            if self.fecha_alta else None
        )
        d["Fuente de Captacion"] = self.fuente_captacion
        d["Referido"] = self.referido
        d["Notas"] = self.notas
        d["CONSGEN FIRMADO"] = self.consgen_firmado
        return d

    def __repr__(self) -> str:
        return f"<Paciente {self.id_paciente} {self.paciente}>"

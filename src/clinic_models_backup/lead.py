"""Modelo Lead — mapea operacional."BBDD LEADS" en Cloud SQL."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase, ClinicTimestampMixin


class Lead(ClinicTimestampMixin, ClinicBase):
    """Lead (contacto potencial, aun no es paciente)."""

    __tablename__ = "BBDD LEADS"
    __table_args__ = {"schema": "operacional"}

    id_lead: Mapped[str] = mapped_column(
        "ID Lead", String(50), primary_key=True
    )
    nombre: Mapped[Optional[str]] = mapped_column(
        "Apellido y Nombre", String(200)
    )
    telefono: Mapped[str] = mapped_column(
        "Telefono (Whatsapp)", String(30), nullable=False, index=True
    )
    email: Mapped[Optional[str]] = mapped_column(
        "email", String(200)
    )
    fecha_creacion: Mapped[Optional[date]] = mapped_column(
        "Fecha Creacion", Date, server_default="CURRENT_DATE"
    )
    estado: Mapped[Optional[str]] = mapped_column(
        "Estado del Lead (Temp)", String(50), default="Nuevo"
    )
    motivo_interes: Mapped[Optional[str]] = mapped_column(
        "Motivo Interes", String(200)
    )
    fuente_captacion: Mapped[Optional[str]] = mapped_column(
        "Fuente Captacion", String(100)
    )
    notas: Mapped[Optional[str]] = mapped_column(
        "Notas y Seguimientos", Text
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet."""
        return {
            "ID Lead": self.id_lead,
            "Apellido y Nombre": self.nombre,
            "Telefono (Whatsapp)": self.telefono,
            "email": self.email,
            "Fecha Creacion": (
                self.fecha_creacion.strftime("%m/%d/%Y")
                if self.fecha_creacion else None
            ),
            "Estado del Lead (Temp)": self.estado,
            "Motivo Interes": self.motivo_interes,
            "Fuente Captacion": self.fuente_captacion,
            "Notas y Seguimientos": self.notas,
        }

    def __repr__(self) -> str:
        return f"<Lead {self.id_lead} {self.nombre}>"

"""Modelo Alineador — mapea operacional."BBDD ALINEADORES" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase, ClinicTimestampMixin


class Alineador(ClinicTimestampMixin, ClinicBase):
    """Tratamiento de alineadores de un paciente."""

    __tablename__ = "BBDD ALINEADORES"
    __table_args__ = {"schema": "operacional"}

    id_alineadores: Mapped[str] = mapped_column(
        "ID ALINEADORES", String(50), primary_key=True
    )
    id_paciente: Mapped[Optional[str]] = mapped_column(
        "ID PACIENTE", String(50),
        ForeignKey('operacional."BBDD PACIENTES"."ID Paciente"'),
    )
    paciente: Mapped[Optional[str]] = mapped_column(
        "PACIENTE", String(200)
    )
    estado_tratamiento: Mapped[Optional[str]] = mapped_column(
        "ESTADO TRATAMIENTO", String(50)
    )
    tipo: Mapped[Optional[str]] = mapped_column(
        "1P/3P", String(10)
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet."""
        return {
            "ID ALINEADORES": self.id_alineadores,
            "ID PACIENTE": self.id_paciente,
            "PACIENTE": self.paciente,
            "ESTADO TRATAMIENTO": self.estado_tratamiento,
            "1P/3P": self.tipo,
        }

    def __repr__(self) -> str:
        return f"<Alineador {self.id_alineadores} {self.paciente}>"

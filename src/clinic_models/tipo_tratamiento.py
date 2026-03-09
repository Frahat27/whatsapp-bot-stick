"""Modelo TipoTratamiento — mapea config."LISTA A | tipo tratamientos" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Integer, Interval, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class TipoTratamiento(ClinicBase):
    """Tipo de tratamiento ofrecido por la clinica."""

    __tablename__ = "LISTA A | tipo tratamientos"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[Optional[str]] = mapped_column(
        "Row ID", Text
    )
    id_tipo_tratamiento: Mapped[int] = mapped_column(
        "ID TIPO TRATAMIENTO", Integer, primary_key=True
    )
    tipo_tratamiento: Mapped[Optional[str]] = mapped_column(
        "TIPO DE TRATAMIENTO", Text
    )
    status_servicio: Mapped[Optional[str]] = mapped_column(
        "Status Servicio", Text
    )
    duracion_turno: Mapped[Optional[str]] = mapped_column(
        "Duracion Turno", Interval
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet."""
        return {
            "Row ID": self.row_id,
            "ID TIPO TRATAMIENTO": self.id_tipo_tratamiento,
            "TIPO DE TRATAMIENTO": self.tipo_tratamiento,
            "Status Servicio": self.status_servicio,
            "Duracion Turno": str(self.duracion_turno) if self.duracion_turno else None,
        }

    def __repr__(self) -> str:
        return f"<TipoTratamiento {self.id_tipo_tratamiento} {self.tipo_tratamiento}>"

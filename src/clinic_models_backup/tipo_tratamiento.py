"""Modelo TipoTratamiento — mapea config."LISTA A I tipo tratamientos" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase, ClinicTimestampMixin


class TipoTratamiento(ClinicTimestampMixin, ClinicBase):
    """Tipo de tratamiento con duracion del turno."""

    __tablename__ = "LISTA A I tipo tratamientos"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    tipo: Mapped[str] = mapped_column(
        "Tipo", String(200), nullable=False
    )
    duracion_turno: Mapped[Optional[int]] = mapped_column(
        "Duracion Turno", Integer, default=30
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet."""
        return {
            "Row ID": self.row_id,
            "Tipo": self.tipo,
            "Duracion Turno": self.duracion_turno,
        }

    def __repr__(self) -> str:
        return f"<TipoTratamiento {self.tipo} {self.duracion_turno}min>"

"""Modelo Produccion — mapea operacional."BBDD PRODUCCION" en Cloud SQL."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Produccion(ClinicBase):
    """Registro de produccion de alineadores."""

    __tablename__ = "BBDD PRODUCCION"
    __table_args__ = {"schema": "operacional"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    id_alineadores: Mapped[Optional[str]] = mapped_column(
        "ID ALINEADORES", Text
    )
    status_produccion: Mapped[Optional[str]] = mapped_column(
        "STATUS PRODUCCION", Text, default="PLANIFICADO"
    )
    fecha_producido: Mapped[Optional[date]] = mapped_column(
        "FECHA PRODUCIDO", Date
    )
    impresora: Mapped[Optional[str]] = mapped_column(
        "IMPRESORA", Text
    )
    lav_sec: Mapped[Optional[str]] = mapped_column(
        "LAV/SEC", Text
    )
    estampadora: Mapped[Optional[str]] = mapped_column(
        "ESTAMPADORA", Text
    )
    resina: Mapped[Optional[str]] = mapped_column(
        "RESINA", Text
    )
    ultima_entrega: Mapped[Optional[date]] = mapped_column(
        "ULTIMA ENTREGA", Date
    )

    def __repr__(self) -> str:
        return f"<Produccion {self.row_id} {self.status_produccion}>"

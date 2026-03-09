"""Modelo InsumoPackaging — mapea config."Lista L | Insumos y Packaging" en Cloud SQL."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class InsumoPackaging(ClinicBase):
    """Insumo o packaging para produccion."""

    __tablename__ = "Lista L | Insumos y Packaging"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    title: Mapped[Optional[str]] = mapped_column(
        "Title", Text
    )
    material: Mapped[Optional[str]] = mapped_column(
        "Material", Text
    )
    categoria: Mapped[Optional[str]] = mapped_column(
        "Categoria", Text
    )
    date: Mapped[Optional[date]] = mapped_column(
        "Date", Date
    )

    def __repr__(self) -> str:
        return f"<InsumoPackaging {self.row_id} {self.title}>"

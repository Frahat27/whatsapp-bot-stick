"""Modelo InsumoStock — mapea operacional."BBDD INSUMOS y STOCK" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class InsumoStock(ClinicBase):
    """Insumo y su stock en la clinica."""

    __tablename__ = "BBDD INSUMOS y STOCK"
    __table_args__ = {"schema": "operacional"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    untitled_text: Mapped[Optional[str]] = mapped_column(
        "Untitled Text", Text
    )
    untitled_dropdown: Mapped[Optional[str]] = mapped_column(
        "Untitled Dropdown", Text
    )
    id_insumo: Mapped[Optional[str]] = mapped_column(
        "ID INSUMO", Text
    )
    insumo: Mapped[Optional[str]] = mapped_column(
        "INSUMO", Text
    )
    stock_disponible: Mapped[Optional[str]] = mapped_column(
        "STOCK DISPOIBLE", Text
    )
    punto_reorden: Mapped[Optional[str]] = mapped_column(
        "PUNTO REORDEN", Text
    )
    status_reabastecimiento: Mapped[Optional[str]] = mapped_column(
        "STATUS REABASTECIMIENTO", Text
    )
    id_proveedor: Mapped[Optional[str]] = mapped_column(
        "ID PROVEEDOR", Text
    )

    def __repr__(self) -> str:
        return f"<InsumoStock {self.row_id} {self.insumo}>"

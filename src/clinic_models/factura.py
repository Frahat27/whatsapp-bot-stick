"""Modelo Factura — mapea operacional."BBDD FACTURAS" en Cloud SQL."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Date, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Factura(ClinicBase):
    """Factura emitida a un paciente."""

    __tablename__ = "BBDD FACTURAS"
    __table_args__ = {"schema": "operacional"}

    row_id: Mapped[str] = mapped_column(
        "Row ID", String(50), primary_key=True
    )
    id_paciente: Mapped[Optional[str]] = mapped_column(
        "ID PACIENTE", Text
    )
    paciente: Mapped[Optional[str]] = mapped_column(
        "PACIENTE", Text
    )
    whatsapp: Mapped[Optional[str]] = mapped_column(
        "Whatsapp", Text
    )
    id_sesion: Mapped[Optional[str]] = mapped_column(
        "ID Sesion", Text
    )
    fecha_emision: Mapped[Optional[date]] = mapped_column(
        "Fecha Emision", Date
    )
    tipo_documento: Mapped[Optional[str]] = mapped_column(
        "Tipo Documento", Text, default="DNI"
    )
    n_documento: Mapped[Optional[str]] = mapped_column(
        "N Documento", Text
    )
    condicion_iva: Mapped[Optional[str]] = mapped_column(
        "Condicion IVA", Text, default="5"
    )
    # 4 lineas de items (hardcoded en AppSheet)
    item_1: Mapped[Optional[str]] = mapped_column("1- Item", Text)
    cant_1: Mapped[Optional[Decimal]] = mapped_column("1- Cant", Numeric(12, 2))
    precio_1: Mapped[Optional[Decimal]] = mapped_column("1- Precio unitario", Numeric(12, 2))
    item_2: Mapped[Optional[str]] = mapped_column("2- Item", Text)
    cant_2: Mapped[Optional[Decimal]] = mapped_column("2- Cant", Numeric(12, 2))
    precio_2: Mapped[Optional[Decimal]] = mapped_column("2- Precio unitario", Numeric(12, 2))
    item_3: Mapped[Optional[str]] = mapped_column("3- Item", Text)
    cant_3: Mapped[Optional[Decimal]] = mapped_column("3- Cant", Numeric(12, 2))
    precio_3: Mapped[Optional[Decimal]] = mapped_column("3- Precio unitario", Numeric(12, 2))
    item_4: Mapped[Optional[str]] = mapped_column("4- Item", Text)
    cant_4: Mapped[Optional[Decimal]] = mapped_column("4- Cant", Numeric(12, 2))
    precio_4: Mapped[Optional[Decimal]] = mapped_column("4- Precio unitario", Numeric(12, 2))

    def __repr__(self) -> str:
        return f"<Factura {self.row_id} {self.paciente}>"

"""Modelo Proveedor — mapea operacional."BBDD PROVEEDORES" en Cloud SQL."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Date, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Proveedor(ClinicBase):
    """Proveedor de insumos de la clinica."""

    __tablename__ = "BBDD PROVEEDORES"
    __table_args__ = {"schema": "operacional"}

    id_proveedor: Mapped[int] = mapped_column(
        "ID Proveedor", Integer, primary_key=True
    )
    proveedor: Mapped[Optional[str]] = mapped_column(
        "Proveedor", Text
    )
    email: Mapped[Optional[str]] = mapped_column(
        "email", Text
    )
    telefono: Mapped[Optional[str]] = mapped_column(
        "Telefono (Whatsapp)", Text
    )
    cuit: Mapped[Optional[int]] = mapped_column(
        "CUIT", Numeric
    )
    direccion: Mapped[Optional[str]] = mapped_column(
        "Direccion", Text
    )
    banco: Mapped[Optional[str]] = mapped_column(
        "Banco", Text
    )
    cbu: Mapped[Optional[int]] = mapped_column(
        "CBU", Numeric
    )
    alias: Mapped[Optional[str]] = mapped_column(
        "Alias", Text
    )
    fecha_ultima_compra: Mapped[Optional[date]] = mapped_column(
        "Fecha ultima compra", Date
    )
    insumo: Mapped[Optional[str]] = mapped_column(
        "Insumo", Text
    )
    estado_proveedor: Mapped[Optional[str]] = mapped_column(
        "Estado Proveedor", Text
    )
    gastos_acumulados: Mapped[Optional[Decimal]] = mapped_column(
        "Gastos acumulados ($)", Numeric(12, 2)
    )

    def __repr__(self) -> str:
        return f"<Proveedor {self.id_proveedor} {self.proveedor}>"

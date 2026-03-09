"""Modelo Gasto — mapea operacional."BBDD GASTOS" en Cloud SQL."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Date, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Gasto(ClinicBase):
    """Gasto registrado de la clinica."""

    __tablename__ = "BBDD GASTOS"
    __table_args__ = {"schema": "operacional"}

    id_gasto: Mapped[int] = mapped_column(
        "ID Gasto", Integer, primary_key=True
    )
    fecha_gasto: Mapped[Optional[date]] = mapped_column(
        "Fecha de gasto", Date
    )
    tipo_gasto: Mapped[Optional[str]] = mapped_column(
        "Tipo de gasto", Text
    )
    tipo_gasto_detalle: Mapped[Optional[str]] = mapped_column(
        "Tipo de gasto (Detalle)", Text
    )
    descripcion: Mapped[Optional[str]] = mapped_column(
        "Descripcion de Gasto", Text
    )
    proveedor: Mapped[Optional[str]] = mapped_column(
        "Proveedor", Text, default="Otro"
    )
    monto: Mapped[Optional[Decimal]] = mapped_column(
        "Monto ($)", Numeric(12, 2)
    )
    metodo_pago: Mapped[Optional[str]] = mapped_column(
        "Metodo de Pago", Text
    )
    factura_proveedor: Mapped[Optional[str]] = mapped_column(
        "Factura proveedor", Text
    )
    moneda: Mapped[Optional[str]] = mapped_column(
        "MONEDA", Text, default="PESOS"
    )
    cantidad_comprada: Mapped[Optional[Decimal]] = mapped_column(
        "Cantidad Comprada", Numeric(12, 2)
    )
    profesionales_empleados: Mapped[Optional[str]] = mapped_column(
        "Profesionales y Empleados", Text
    )
    observaciones: Mapped[Optional[str]] = mapped_column(
        "Observaciones", Text
    )

    def __repr__(self) -> str:
        return f"<Gasto {self.id_gasto} {self.tipo_gasto} ${self.monto}>"

"""Modelo Alineador — mapea operacional."BBDD ALINEADORES" en Cloud SQL."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Boolean, Date, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class Alineador(ClinicBase):
    """Tratamiento de alineadores de un paciente."""

    __tablename__ = "BBDD ALINEADORES"
    __table_args__ = {"schema": "operacional"}

    id_alineadores: Mapped[int] = mapped_column(
        "ID ALINEADORES", Integer, primary_key=True
    )
    paciente: Mapped[Optional[str]] = mapped_column(
        "PACIENTE", Text
    )
    tipo_tratamiento: Mapped[Optional[str]] = mapped_column(
        "TIPO TRATAMIENTO", Text, default="1era Etapa"
    )
    maxilar: Mapped[Optional[str]] = mapped_column(
        "MAXILAR", Text, default="SUP e INF"
    )
    tipo_produccion: Mapped[Optional[str]] = mapped_column(
        "TIPO DE PRODUCCION", Text, default="MENSUAL"
    )
    fecha_inicio: Mapped[Optional[date]] = mapped_column(
        "FECHA INICIO", Date
    )
    estado_tratamiento: Mapped[Optional[str]] = mapped_column(
        "ESTADO TRATAMIENTO", Text, default="ESCANEADO"
    )
    accion_pendiente: Mapped[Optional[bool]] = mapped_column(
        "ACCION PENDIENTE", Boolean, default=False
    )
    # Alineadores A1-A12 (entregados/no)
    a1: Mapped[Optional[bool]] = mapped_column("A1", Boolean, default=False)
    a2: Mapped[Optional[bool]] = mapped_column("A2", Boolean, default=False)
    a3: Mapped[Optional[bool]] = mapped_column("A3", Boolean, default=False)
    a4: Mapped[Optional[bool]] = mapped_column("A4", Boolean, default=False)
    a5: Mapped[Optional[bool]] = mapped_column("A5", Boolean, default=False)
    a6: Mapped[Optional[bool]] = mapped_column("A6", Boolean, default=False)
    a7: Mapped[Optional[bool]] = mapped_column("A7", Boolean, default=False)
    a8: Mapped[Optional[bool]] = mapped_column("A8", Boolean, default=False)
    a9: Mapped[Optional[bool]] = mapped_column("A9", Boolean, default=False)
    a10: Mapped[Optional[bool]] = mapped_column("A10", Boolean, default=False)
    a11: Mapped[Optional[bool]] = mapped_column("A11", Boolean, default=False)
    a12: Mapped[Optional[bool]] = mapped_column("A12", Boolean, default=False)
    co: Mapped[Optional[bool]] = mapped_column("CO", Boolean, default=False)
    presupuesto: Mapped[Optional[Decimal]] = mapped_column(
        "PRESUPUESTO", Numeric(12, 2)
    )
    nps_tratamiento: Mapped[Optional[int]] = mapped_column(
        "NPS TRATAMIENTO", Integer
    )
    notas_clinicas: Mapped[Optional[str]] = mapped_column(
        "NOTAS CLINICAS", Text
    )
    adjuntos: Mapped[Optional[str]] = mapped_column(
        "ADJUNTOS", Text
    )
    # Produccion P1, P2, P CO
    p1: Mapped[Optional[bool]] = mapped_column("P1", Boolean, default=False)
    p2: Mapped[Optional[bool]] = mapped_column("P2", Boolean, default=False)
    p_co: Mapped[Optional[bool]] = mapped_column("P CO", Boolean, default=False)
    fecha_update: Mapped[Optional[date]] = mapped_column(
        "FECHA UPDATE", Date
    )
    identificador: Mapped[Optional[str]] = mapped_column(
        "IDENTIFICADOR", Text
    )
    un_p_tres_p: Mapped[Optional[str]] = mapped_column(
        "1P/3P", Text
    )
    id_paciente: Mapped[Optional[str]] = mapped_column(
        "ID PACIENTE", Text
    )

    def to_appsheet_dict(self) -> dict[str, Any]:
        """Dict con nombres exactos de AppSheet."""
        return {
            "ID ALINEADORES": self.id_alineadores,
            "PACIENTE": self.paciente,
            "TIPO TRATAMIENTO": self.tipo_tratamiento,
            "MAXILAR": self.maxilar,
            "TIPO DE PRODUCCION": self.tipo_produccion,
            "FECHA INICIO": (
                self.fecha_inicio.strftime("%m/%d/%Y")
                if self.fecha_inicio else None
            ),
            "ESTADO TRATAMIENTO": self.estado_tratamiento,
            "ACCION PENDIENTE": self.accion_pendiente,
            "A1": self.a1, "A2": self.a2, "A3": self.a3,
            "A4": self.a4, "A5": self.a5, "A6": self.a6,
            "A7": self.a7, "A8": self.a8, "A9": self.a9,
            "A10": self.a10, "A11": self.a11, "A12": self.a12,
            "CO": self.co,
            "PRESUPUESTO": float(self.presupuesto) if self.presupuesto else None,
            "NPS TRATAMIENTO": self.nps_tratamiento,
            "NOTAS CLINICAS": self.notas_clinicas,
            "ADJUNTOS": self.adjuntos,
            "P1": self.p1, "P2": self.p2, "P CO": self.p_co,
            "FECHA UPDATE": (
                self.fecha_update.strftime("%m/%d/%Y")
                if self.fecha_update else None
            ),
            "IDENTIFICADOR": self.identificador,
            "1P/3P": self.un_p_tres_p,
            "ID PACIENTE": self.id_paciente,
        }

    def __repr__(self) -> str:
        return f"<Alineador {self.id_alineadores} {self.paciente}>"

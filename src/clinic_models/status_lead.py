"""Modelo StatusLead — mapea config."LISTA C | STATUS LEAD" en Cloud SQL."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.clinic_models.base import ClinicBase


class StatusLead(ClinicBase):
    """Estado posible de un lead."""

    __tablename__ = "LISTA C | STATUS LEAD"
    __table_args__ = {"schema": "config"}

    row_id: Mapped[Optional[str]] = mapped_column("Row ID", Text)
    id_temp_lead: Mapped[int] = mapped_column(
        "ID Temp Lead", Integer, primary_key=True
    )
    status_lead: Mapped[Optional[str]] = mapped_column(
        "Status Lead", Text
    )

    def __repr__(self) -> str:
        return f"<StatusLead {self.id_temp_lead} {self.status_lead}>"

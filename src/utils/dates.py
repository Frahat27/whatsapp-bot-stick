"""
Utilidades de conversión de fechas para AppSheet API.

REGLA CRÍTICA: AppSheet API SIEMPRE espera MM/DD/YYYY.
El front-end muestra DD/M/YY pero la API rechaza ese formato con 400.
"""

from datetime import date, datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

# Timezone de Argentina
BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")


def to_appsheet_date(d: date) -> str:
    """
    Convierte date a formato AppSheet API: MM/DD/YYYY.

    Ejemplo: date(2026, 3, 15) → "03/15/2026"
    """
    return d.strftime("%m/%d/%Y")


def from_appsheet_date(date_str: str) -> Optional[date]:
    """
    Parsea fecha de AppSheet (MM/DD/YYYY) a date.

    Ejemplo: "03/15/2026" → date(2026, 3, 15)
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%m/%d/%Y").date()
    except ValueError:
        return None


def to_appsheet_time(t: time) -> str:
    """
    Convierte time a formato AppSheet: HH:MM:SS.

    Ejemplo: time(14, 30) → "14:30:00"
    """
    return t.strftime("%H:%M:%S")


def from_appsheet_time(time_str: str) -> Optional[time]:
    """
    Parsea hora de AppSheet (HH:MM:SS) a time.

    Ejemplo: "14:30:00" → time(14, 30, 0)
    """
    if not time_str:
        return None
    try:
        return datetime.strptime(time_str, "%H:%M:%S").time()
    except ValueError:
        return None


def now_argentina() -> datetime:
    """Datetime actual en zona horaria Argentina."""
    return datetime.now(BUENOS_AIRES)


def today_argentina() -> date:
    """Fecha actual en zona horaria Argentina."""
    return now_argentina().date()


def today_appsheet() -> str:
    """Fecha actual en formato AppSheet MM/DD/YYYY."""
    return to_appsheet_date(today_argentina())

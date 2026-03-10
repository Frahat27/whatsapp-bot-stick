"""
Cliente Google Sheets — Hoja "Tareas Pendientes WhatsApp".

Columnas (A-L) según google_sheets_estructura.md:
A: Fecha Creación      (datetime, auto)
B: Tipo                (dropdown: Coordinación Endodoncia, Urgencia, etc.)
C: Prioridad           (dropdown: 🔴 Alta, 🟡 Normal)
D: Paciente            (nombre)
E: Teléfono            (WhatsApp)
F: ID Paciente         (AppSheet ID, si existe)
G: Profesional         (especialista, si aplica)
H: Contexto            (descripción detallada)
I: Estado              (Pendiente / En proceso / Resuelto)
J: Resuelta por        (manual)
K: Fecha Resolución    (manual)
L: Notas Resolución    (manual)
"""

import asyncio
import json
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from src.config import get_settings
from src.utils.dates import now_argentina
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

# Tipos de tarea válidos
TASK_TYPES = {
    "Coordinación Endodoncia",
    "Coordinación Implantes",
    "Coordinación Cirugía",
    "Urgencia",
    "Reprogramación",
    "Sin disponibilidad",
    "Consulta sin respuesta",
    "Factura pendiente",
}

# Profesional por defecto según tipo de coordinación
PROFESIONAL_MAP = {
    "Coordinación Endodoncia": "Nacho Fernández",
    "Coordinación Implantes": "Diego Figueiras",
    "Coordinación Cirugía": "Dai Pérez",
}


def _get_gspread_client() -> gspread.Client:
    """
    Crea un cliente gspread autenticado con service account.

    Prioridad:
    1. GOOGLE_SHEETS_CREDENTIALS_JSON env var (Docker/Railway)
    2. credentials/franco.json file (local dev)
    """
    settings = get_settings()

    if settings.google_sheets_credentials_json:
        # Production: JSON string desde variable de entorno
        creds_info = json.loads(settings.google_sheets_credentials_json)
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    else:
        # Local dev: archivo de credenciales
        creds = Credentials.from_service_account_file(
            settings.google_sheets_credentials_file,
            scopes=SCOPES,
        )

    return gspread.authorize(creds)


def _get_worksheet() -> gspread.Worksheet:
    """Obtiene la primera hoja del spreadsheet de tareas pendientes."""
    settings = get_settings()
    gc = _get_gspread_client()
    spreadsheet = gc.open_by_key(settings.google_sheets_spreadsheet_id)
    return spreadsheet.sheet1


async def add_pending_task(
    tipo: str,
    contexto: str,
    paciente: str = "",
    telefono: str = "",
    paciente_id: str = "",
    profesional: str = "",
    prioridad: str = "🟡 Normal",
) -> dict:
    """
    Agregar una tarea a la hoja de Tareas Pendientes.

    Args:
        tipo: Tipo de tarea (ver TASK_TYPES)
        contexto: Descripción detallada de la situación
        paciente: Nombre del paciente
        telefono: Teléfono WhatsApp
        paciente_id: ID del paciente en AppSheet (si existe)
        profesional: Especialista relacionado (auto para coordinaciones)
        prioridad: "🔴 Alta" o "🟡 Normal"

    Returns:
        Dict con resultado de la operación.
    """
    # Auto-asignar profesional si es coordinación y no se especificó
    if not profesional and tipo in PROFESIONAL_MAP:
        profesional = PROFESIONAL_MAP[tipo]

    # Urgencias siempre prioridad alta
    if tipo == "Urgencia":
        prioridad = "🔴 Alta"

    fecha = now_argentina().strftime("%Y-%m-%d %H:%M")

    row = [
        fecha,          # A: Fecha Creación
        tipo,           # B: Tipo
        prioridad,      # C: Prioridad
        paciente,       # D: Paciente
        telefono,       # E: Teléfono
        paciente_id,    # F: ID Paciente
        profesional,    # G: Profesional
        contexto,       # H: Contexto
        "Pendiente",    # I: Estado
        "",             # J: Resuelta por
        "",             # K: Fecha Resolución
        "",             # L: Notas Resolución
    ]

    logger.info(
        "gsheets_add_task",
        tipo=tipo,
        prioridad=prioridad,
        paciente=paciente,
    )

    try:
        # gspread es sincrónico → ejecutar en thread pool
        worksheet = await asyncio.to_thread(_get_worksheet)
        result = await asyncio.to_thread(worksheet.append_row, row)

        logger.info("gsheets_task_created", tipo=tipo, paciente=paciente)

        return {
            "status": "ok",
            "row": result,
            "task": {
                "fecha": fecha,
                "tipo": tipo,
                "prioridad": prioridad,
                "paciente": paciente,
                "contexto": contexto,
            },
        }
    except FileNotFoundError:
        logger.error(
            "gsheets_credentials_not_found",
            path=get_settings().google_sheets_credentials_file,
        )
        return {"status": "error", "error": "Archivo de credenciales no encontrado"}
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(
            "gsheets_spreadsheet_not_found",
            spreadsheet_id=get_settings().google_sheets_spreadsheet_id,
        )
        return {"status": "error", "error": "Spreadsheet no encontrado"}
    except Exception as e:
        logger.error("gsheets_error", error=str(e), tipo=tipo)
        return {"status": "error", "error": str(e)}


async def get_pending_tasks(estado: str = "Pendiente") -> list[dict]:
    """
    Obtiene tareas filtradas por estado.
    Ignora la fila 2 (descripciones de columnas).

    Returns:
        Lista de dicts con los datos de cada tarea + _row_number.
    """
    try:
        worksheet = await asyncio.to_thread(_get_worksheet)
        all_rows = await asyncio.to_thread(worksheet.get_all_records)

        tasks = []
        for i, row in enumerate(all_rows):
            # Fila real = índice + 2 (fila 1 es header, datos empiezan en fila 2)
            row_number = i + 2
            # Saltar fila 2 (descripciones) — tiene "Timestamp automático" en col A
            if row_number == 2:
                continue
            if row.get("Estado", "") == estado:
                row["_row_number"] = row_number
                tasks.append(row)

        logger.info("gsheets_get_tasks", estado=estado, count=len(tasks))
        return tasks
    except Exception as e:
        logger.error("gsheets_get_error", error=str(e))
        return []


async def update_task_status(
    row_number: int,
    estado: str,
    resuelta_por: str = "",
    notas: str = "",
) -> dict:
    """
    Actualiza el estado de una tarea (columnas I, J, K, L).

    Args:
        row_number: Número de fila (1-indexed, incluye header).
        estado: Nuevo estado ("En proceso" o "Resuelto").
        resuelta_por: Quién resolvió.
        notas: Notas de resolución.
    """
    try:
        worksheet = await asyncio.to_thread(_get_worksheet)

        # I=9, J=10, K=11, L=12 (1-indexed)
        await asyncio.to_thread(worksheet.update_cell, row_number, 9, estado)

        if resuelta_por:
            await asyncio.to_thread(
                worksheet.update_cell, row_number, 10, resuelta_por
            )

        if estado == "Resuelto":
            fecha_res = now_argentina().strftime("%Y-%m-%d")
            await asyncio.to_thread(
                worksheet.update_cell, row_number, 11, fecha_res
            )

        if notas:
            await asyncio.to_thread(worksheet.update_cell, row_number, 12, notas)

        logger.info(
            "gsheets_task_updated", row=row_number, estado=estado
        )
        return {"status": "ok", "row": row_number, "estado": estado}
    except Exception as e:
        logger.error("gsheets_update_error", error=str(e), row=row_number)
        return {"status": "error", "error": str(e)}

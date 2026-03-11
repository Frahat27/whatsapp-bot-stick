"""
AppSheet Sync Trigger — fuerza refresh instantáneo en AppSheet.

Después de cada escritura en Cloud SQL (agendar, modificar, cancelar turno,
registrar pago, crear paciente/lead), dispara un Edit a la API de AppSheet
con los mismos datos. Esto fuerza a AppSheet a re-leer la tabla y mostrar
el cambio en segundos.

Características:
- Fire-and-forget: no bloquea el flujo del bot
- Tolerante a fallos: si AppSheet no responde, el bot sigue funcionando
- Rate limit aware: respeta el intervalo mínimo de AppSheet (45s)
- Logging: registra éxito/fallo para diagnóstico
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Mapeo de tabla → campo KEY primario de AppSheet
_TABLE_KEYS: dict[str, str] = {
    "BBDD SESIONES": "ID Sesion",
    "BBDD PACIENTES": "ID Paciente",
    "BBDD LEADS": "ID Lead",
    "BBDD PAGOS": "ID Pago",
}


async def trigger_appsheet_sync(
    table: str,
    row_data: dict[str, Any],
    action: str = "Edit",
) -> None:
    """
    Dispara un sync fire-and-forget a AppSheet.

    Lanza la llamada como tarea async en background para no bloquear.
    Si falla, loguea el error pero no propaga la excepción.

    Args:
        table: Nombre exacto de la tabla AppSheet (ej: "BBDD SESIONES")
        row_data: Dict con los campos del registro (resultado de to_appsheet_dict())
        action: "Edit" para updates, "Add" para nuevos registros
    """
    # Validar que el row tiene la key primaria
    key_field = _TABLE_KEYS.get(table)
    if key_field and not row_data.get(key_field):
        logger.warning(
            "appsheet_sync_skip_no_key",
            table=table,
            key_field=key_field,
        )
        return

    # Lanzar en background (fire-and-forget)
    asyncio.create_task(_do_sync(table, row_data, action))


async def _do_sync(
    table: str,
    row_data: dict[str, Any],
    action: str,
) -> None:
    """Ejecuta el sync real contra la API de AppSheet."""
    try:
        from src.clients.appsheet import get_appsheet_client

        client = get_appsheet_client()

        # Verificar que tiene API key configurada
        if not client.api_key:
            logger.debug("appsheet_sync_skip_no_api_key")
            return

        # Limpiar campos None del row_data para evitar errores de AppSheet
        clean_row = {k: v for k, v in row_data.items() if v is not None}

        if action == "Add":
            await client.add(table, [clean_row])
        else:
            await client.edit(table, [clean_row])

        logger.info(
            "appsheet_sync_ok",
            table=table,
            action=action,
            row_key=clean_row.get(_TABLE_KEYS.get(table, ""), "?"),
        )

    except Exception as e:
        # Nunca propagar — el dato ya está en Cloud SQL
        logger.warning(
            "appsheet_sync_error",
            table=table,
            action=action,
            error=str(e),
        )

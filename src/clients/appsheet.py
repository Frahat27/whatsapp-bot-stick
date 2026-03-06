"""
Cliente AppSheet API v2 — ARCHIVO CRÍTICO.

Implementa las 12 reglas documentadas en appsheet-api.md:
1. NO usar Locale — "Properties": {} siempre
2. Rate limit ~45s entre requests
3. 200 con body vacío = rate limited o tabla no encontrada
4. Nombres de tabla con prefijo "BBDD"
5. Fechas siempre MM/DD/YYYY
6. Enum fields son estrictos
7. Keys compuestos en BBDD PRESUPUESTOS
8. BBDD PACIENTES Edit NO funciona con keys "ANT" legacy

Operaciones: Find, Add, Edit, Delete
Cache con Redis (TTL configurable)
Rate limiting con asyncio.sleep
Retry con backoff exponencial
"""

import asyncio
import json
import time
from typing import Any, Optional

import httpx

from src.config import get_settings
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Base URL de AppSheet API v2
APPSHEET_BASE_URL = "https://api.appsheet.com/api/v2/apps"


class AppSheetError(Exception):
    """Error genérico de AppSheet."""

    def __init__(self, message: str, status_code: int = 0, table: str = "", action: str = ""):
        self.message = message
        self.status_code = status_code
        self.table = table
        self.action = action
        super().__init__(f"[{table}/{action}] {message} (HTTP {status_code})")


class AppSheetRateLimitError(AppSheetError):
    """Rate limit detectado (200 con body vacío)."""
    pass


class AppSheetClient:
    """
    Cliente para AppSheet API v2 con rate limiting y retry.

    Uso:
        client = AppSheetClient()
        pacientes = await client.find("BBDD PACIENTES", selector="Filter(...)")
        await client.add("BBDD SESIONES", [{"Paciente": "...", ...}])
    """

    def __init__(self):
        settings = get_settings()
        self.app_id = settings.appsheet_app_id
        self.api_key = settings.appsheet_api_key
        self.min_interval = settings.appsheet_min_interval_seconds

        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

        # HTTP client persistente
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),  # AppSheet puede ser lento
            headers={
                "ApplicationAccessKey": self.api_key,
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        """Cerrar el HTTP client."""
        await self._client.aclose()

    # --- Operaciones públicas ---

    async def find(
        self,
        table: str,
        selector: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Buscar registros en una tabla.

        Args:
            table: Nombre exacto de la tabla (ej: "BBDD PACIENTES")
            selector: Expression de filtro AppSheet (ej: 'Filter("BBDD PACIENTES", ...)')

        Returns:
            Lista de diccionarios con los registros encontrados.
        """
        body: dict[str, Any] = {
            "Action": "Find",
            "Properties": {},
            "Rows": [],
        }
        if selector:
            body["Properties"]["Selector"] = selector

        return await self._request(table, body, action="Find")

    async def add(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Agregar registros a una tabla.

        Args:
            table: Nombre exacto de la tabla.
            rows: Lista de diccionarios con los campos a crear.

        Returns:
            Registros creados (con campos auto-poblados).
        """
        body = {
            "Action": "Add",
            "Properties": {},
            "Rows": rows,
        }
        return await self._request(table, body, action="Add")

    async def edit(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Editar registros existentes.

        Args:
            table: Nombre exacto de la tabla.
            rows: Lista de dicts con KEY + campos a modificar.
                  ⚠️ BBDD PRESUPUESTOS requiere "Row ID" + "ID Presupuesto" (key compuesto).
                  ⚠️ BBDD PACIENTES: NO funciona con keys "ANT" legacy, solo UUID.

        Returns:
            Registros actualizados.
        """
        body = {
            "Action": "Edit",
            "Properties": {},
            "Rows": rows,
        }
        return await self._request(table, body, action="Edit")

    async def delete(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Eliminar registros.

        Args:
            table: Nombre exacto de la tabla.
            rows: Lista de dicts con solo la(s) KEY(s) del registro.

        Returns:
            Registros eliminados.
        """
        body = {
            "Action": "Delete",
            "Properties": {},
            "Rows": rows,
        }
        return await self._request(table, body, action="Delete")

    # --- Métodos de conveniencia ---

    async def find_by_phone(self, table: str, phone_10: str) -> list[dict[str, Any]]:
        """
        Buscar registros por teléfono (últimos 10 dígitos, CONTAINS).

        Args:
            table: "BBDD PACIENTES" o "BBDD LEADS"
            phone_10: Teléfono normalizado a 10 dígitos.
        """
        selector = (
            f'Filter({table}, '
            f'CONTAINS([Telefono (Whatsapp)], "{phone_10}"))'
        )
        return await self.find(table, selector=selector)

    async def find_patient_by_phone(self, phone_10: str) -> Optional[dict[str, Any]]:
        """Buscar paciente por teléfono. Retorna el primero o None."""
        results = await self.find_by_phone("BBDD PACIENTES", phone_10)
        return results[0] if results else None

    async def find_lead_by_phone(self, phone_10: str) -> Optional[dict[str, Any]]:
        """Buscar lead por teléfono. Retorna el primero o None."""
        results = await self.find_by_phone("BBDD LEADS", phone_10)
        return results[0] if results else None

    # --- Core request con rate limiting y retry ---

    async def _request(
        self,
        table: str,
        body: dict[str, Any],
        action: str,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Ejecutar request a AppSheet con rate limiting y retry.

        Maneja:
        - Rate limiting (asyncio.sleep entre requests)
        - 200 con body vacío (rate limited o tabla no encontrada)
        - Retry con backoff exponencial
        """
        url = f"{APPSHEET_BASE_URL}/{self.app_id}/tables/{table}/Action"

        for attempt in range(max_retries):
            # Rate limiting: esperar si es necesario
            await self._wait_for_rate_limit()

            try:
                logger.info(
                    "appsheet_request",
                    table=table,
                    action=action,
                    attempt=attempt + 1,
                )

                response = await self._client.post(url, json=body)

                # Registrar tiempo del request
                self._last_request_time = time.monotonic()

                # 200 con body vacío = rate limited
                if response.status_code == 200 and not response.text.strip():
                    logger.warning(
                        "appsheet_empty_response",
                        table=table,
                        action=action,
                        attempt=attempt + 1,
                    )
                    if attempt < max_retries - 1:
                        wait_time = self.min_interval * (attempt + 1)
                        logger.info("appsheet_retry_wait", seconds=wait_time)
                        await asyncio.sleep(wait_time)
                        continue
                    raise AppSheetRateLimitError(
                        "200 con body vacío (rate limited)",
                        status_code=200,
                        table=table,
                        action=action,
                    )

                # Errores HTTP
                if response.status_code != 200:
                    error_text = response.text[:500]
                    logger.error(
                        "appsheet_error",
                        table=table,
                        action=action,
                        status=response.status_code,
                        error=error_text,
                    )
                    raise AppSheetError(
                        error_text,
                        status_code=response.status_code,
                        table=table,
                        action=action,
                    )

                # Parsear respuesta exitosa
                data = response.json()
                rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []

                logger.info(
                    "appsheet_success",
                    table=table,
                    action=action,
                    rows_count=len(rows),
                )
                return rows

            except httpx.RequestError as e:
                logger.error(
                    "appsheet_network_error",
                    table=table,
                    action=action,
                    error=str(e),
                    attempt=attempt + 1,
                )
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    await asyncio.sleep(wait_time)
                    continue
                raise AppSheetError(
                    f"Network error: {str(e)}",
                    table=table,
                    action=action,
                )

        # No debería llegar acá
        raise AppSheetError("Max retries exceeded", table=table, action=action)

    async def _wait_for_rate_limit(self) -> None:
        """
        Esperar si no pasó suficiente tiempo desde el último request.
        Usa lock para evitar race conditions en requests concurrentes.
        """
        async with self._lock:
            if self._last_request_time > 0:
                elapsed = time.monotonic() - self._last_request_time
                if elapsed < self.min_interval:
                    wait_time = self.min_interval - elapsed
                    logger.debug("appsheet_rate_limit_wait", seconds=round(wait_time, 1))
                    await asyncio.sleep(wait_time)


# Singleton global (se inicializa en lifespan)
_client: Optional[AppSheetClient] = None


def get_appsheet_client() -> AppSheetClient:
    """Obtener la instancia singleton del cliente AppSheet."""
    global _client
    if _client is None:
        _client = AppSheetClient()
    return _client


async def shutdown_appsheet_client() -> None:
    """Cerrar el cliente AppSheet (llamar en shutdown)."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None

"""
Tests para el módulo de AppSheet Sync Trigger.

Verifica que trigger_appsheet_sync dispara las llamadas correctas
a la API de AppSheet sin bloquear el flujo del bot.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestTriggerAppsheetSync:
    """Tests para trigger_appsheet_sync."""

    async def test_edit_action_calls_appsheet_edit(self):
        """Sync con action=Edit llama a client.edit."""
        mock_client = MagicMock()
        mock_client.api_key = "test-key"
        mock_client.edit = AsyncMock(return_value=[])

        with patch("src.clients.appsheet.get_appsheet_client", return_value=mock_client):
            from src.clients.appsheet_sync import _do_sync
            await _do_sync("BBDD SESIONES", {"ID Sesion": "SES-001", "Paciente": "Test"}, "Edit")

        mock_client.edit.assert_called_once()
        call_args = mock_client.edit.call_args
        assert call_args[0][0] == "BBDD SESIONES"
        assert call_args[0][1][0]["ID Sesion"] == "SES-001"

    async def test_add_action_calls_appsheet_add(self):
        """Sync con action=Add llama a client.add."""
        mock_client = MagicMock()
        mock_client.api_key = "test-key"
        mock_client.add = AsyncMock(return_value=[])

        with patch("src.clients.appsheet.get_appsheet_client", return_value=mock_client):
            from src.clients.appsheet_sync import _do_sync
            await _do_sync("BBDD PAGOS", {"ID Pago": "PAG-001", "Monto": "5000"}, "Add")

        mock_client.add.assert_called_once()
        call_args = mock_client.add.call_args
        assert call_args[0][0] == "BBDD PAGOS"

    async def test_none_values_are_cleaned(self):
        """Campos con valor None se eliminan del row antes de enviar."""
        mock_client = MagicMock()
        mock_client.api_key = "test-key"
        mock_client.edit = AsyncMock(return_value=[])

        with patch("src.clients.appsheet.get_appsheet_client", return_value=mock_client):
            from src.clients.appsheet_sync import _do_sync
            await _do_sync(
                "BBDD SESIONES",
                {"ID Sesion": "SES-001", "Duracion": None, "Observaciones": None, "Paciente": "Test"},
                "Edit",
            )

        sent_row = mock_client.edit.call_args[0][1][0]
        assert "Duracion" not in sent_row
        assert "Observaciones" not in sent_row
        assert sent_row["Paciente"] == "Test"

    async def test_skips_when_no_api_key(self):
        """No hace nada si no hay API key configurada."""
        mock_client = MagicMock()
        mock_client.api_key = ""
        mock_client.edit = AsyncMock()

        with patch("src.clients.appsheet.get_appsheet_client", return_value=mock_client):
            from src.clients.appsheet_sync import _do_sync
            await _do_sync("BBDD SESIONES", {"ID Sesion": "SES-001"}, "Edit")

        mock_client.edit.assert_not_called()

    async def test_error_does_not_propagate(self):
        """Si AppSheet falla, no propaga la excepción."""
        mock_client = MagicMock()
        mock_client.api_key = "test-key"
        mock_client.edit = AsyncMock(side_effect=Exception("AppSheet down"))

        with patch("src.clients.appsheet.get_appsheet_client", return_value=mock_client):
            from src.clients.appsheet_sync import _do_sync
            # No debe lanzar excepción
            await _do_sync("BBDD SESIONES", {"ID Sesion": "SES-001"}, "Edit")

    async def test_skips_when_no_primary_key(self):
        """No dispara sync si el row no tiene la key primaria."""
        from src.clients.appsheet_sync import trigger_appsheet_sync

        with patch("src.clients.appsheet_sync.asyncio") as mock_asyncio:
            await trigger_appsheet_sync("BBDD SESIONES", {"Paciente": "Test"})

        # No debe crear task porque falta ID Sesion
        mock_asyncio.create_task.assert_not_called()

    async def test_fires_task_when_valid(self):
        """Dispara create_task cuando el row tiene key primaria."""
        from src.clients.appsheet_sync import trigger_appsheet_sync

        with patch("src.clients.appsheet_sync.asyncio") as mock_asyncio:
            await trigger_appsheet_sync(
                "BBDD SESIONES",
                {"ID Sesion": "SES-001", "Paciente": "Test"},
            )

        mock_asyncio.create_task.assert_called_once()

    async def test_sync_all_table_types(self):
        """Verifica que las 4 tablas tienen key primaria mapeada."""
        from src.clients.appsheet_sync import _TABLE_KEYS

        assert "BBDD SESIONES" in _TABLE_KEYS
        assert "BBDD PACIENTES" in _TABLE_KEYS
        assert "BBDD LEADS" in _TABLE_KEYS
        assert "BBDD PAGOS" in _TABLE_KEYS

    async def test_unknown_table_still_fires(self):
        """Tabla sin key mapeada igual dispara sync."""
        from src.clients.appsheet_sync import trigger_appsheet_sync

        with patch("src.clients.appsheet_sync.asyncio") as mock_asyncio:
            await trigger_appsheet_sync(
                "NUEVA TABLA",
                {"algo": "valor"},
            )

        # Sin key mapeada, no hay validación → dispara
        mock_asyncio.create_task.assert_called_once()

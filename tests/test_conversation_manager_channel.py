"""
Tests para ConversationManager con channel="panel".

Verifica que cuando channel="panel", NO se llaman funciones de WhatsApp
(mark_as_read, send_text) pero SÍ se ejecuta el flujo completo (Claude, tools, DB).
"""
from __future__ import annotations

from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import pytest_asyncio

from src.services.conversation_manager import ConversationManager


class TestChannelPanel:
    """ConversationManager con channel='panel' no toca WhatsApp."""

    @pytest.mark.asyncio
    async def test_panel_channel_does_not_call_whatsapp(self):
        """channel='panel' no debe llamar mark_as_read ni send_text."""
        mock_db = AsyncMock()
        # Mock conversation
        mock_conv = MagicMock()
        mock_conv.id = 1
        mock_conv.phone = "1155551234"
        mock_conv.contact_type = None
        mock_conv.patient_id = None
        mock_conv.patient_name = None
        mock_conv.lead_id = None
        mock_conv.state = MagicMock()
        mock_conv.state.status.value = "bot_active"
        # Make state check pass (BOT_ACTIVE)
        from src.models.conversation_state import ConversationStatus
        mock_conv.state.status = ConversationStatus.BOT_ACTIVE
        mock_conv.messages = []
        mock_conv.is_active = True

        # Mock DB execute for _get_or_create_conversation
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.refresh = AsyncMock()

        # Mock message save
        mock_msg = MagicMock()
        mock_msg.id = 100
        mock_msg.role = MagicMock()
        mock_msg.role.value = "user"
        mock_msg.content = "Test"
        mock_msg.created_at = "2026-03-07"

        manager = ConversationManager(mock_db, MagicMock())

        with patch.object(manager, "_save_message", new_callable=AsyncMock, return_value=mock_msg), \
             patch.object(manager, "_identify_contact", new_callable=AsyncMock, return_value={"tipo_contacto": "nuevo", "telefono": "1155551234"}), \
             patch.object(manager, "_build_message_history", return_value=[{"role": "user", "content": "Test"}]), \
             patch.object(manager, "_broadcast_message", new_callable=AsyncMock), \
             patch("src.services.conversation_manager.mark_as_read", new_callable=AsyncMock) as mock_mark_read, \
             patch("src.services.conversation_manager.send_text", new_callable=AsyncMock) as mock_send_text, \
             patch("src.services.conversation_manager.generate_response", new_callable=AsyncMock, return_value="Hola, soy Sofia"):

            result = await manager.handle_incoming_message(
                phone="1155551234",
                content="Test message",
                message_type="text",
                wa_message_id=None,
                contact_name="Test User",
                channel="panel",
            )

            # Verificar que NO se llamaron funciones de WhatsApp
            mock_mark_read.assert_not_called()
            mock_send_text.assert_not_called()

            # Pero SÍ se generó respuesta
            assert result == "Hola, soy Sofia"

    @pytest.mark.asyncio
    async def test_whatsapp_channel_calls_whatsapp(self):
        """channel='whatsapp' SÍ debe llamar mark_as_read y send_text."""
        mock_db = AsyncMock()
        mock_conv = MagicMock()
        mock_conv.id = 1
        mock_conv.phone = "1155551234"
        mock_conv.contact_type = None
        mock_conv.patient_id = None
        mock_conv.patient_name = None
        mock_conv.lead_id = None
        from src.models.conversation_state import ConversationStatus
        mock_conv.state = MagicMock()
        mock_conv.state.status = ConversationStatus.BOT_ACTIVE
        mock_conv.messages = []
        mock_conv.is_active = True

        # First execute = _get_or_create_conversation (returns conv)
        # Second execute = _check_duplicate (returns None = not duplicate)
        mock_result_conv = MagicMock()
        mock_result_conv.scalar_one_or_none.return_value = mock_conv
        mock_result_dedup = MagicMock()
        mock_result_dedup.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(side_effect=[mock_result_conv, mock_result_dedup])
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.refresh = AsyncMock()

        mock_msg = MagicMock()
        mock_msg.id = 100
        mock_msg.role = MagicMock()
        mock_msg.role.value = "user"
        mock_msg.content = "Test"
        mock_msg.created_at = "2026-03-07"

        manager = ConversationManager(mock_db, MagicMock())

        with patch.object(manager, "_save_message", new_callable=AsyncMock, return_value=mock_msg), \
             patch.object(manager, "_identify_contact", new_callable=AsyncMock, return_value={"tipo_contacto": "nuevo", "telefono": "1155551234"}), \
             patch.object(manager, "_build_message_history", return_value=[{"role": "user", "content": "Test"}]), \
             patch.object(manager, "_broadcast_message", new_callable=AsyncMock), \
             patch("src.services.conversation_manager.mark_as_read", new_callable=AsyncMock) as mock_mark_read, \
             patch("src.services.conversation_manager.send_text", new_callable=AsyncMock) as mock_send_text, \
             patch("src.services.conversation_manager.to_whatsapp_format", return_value="5491155551234") as mock_format, \
             patch("src.services.conversation_manager.generate_response", new_callable=AsyncMock, return_value="Hola, soy Sofia"):

            result = await manager.handle_incoming_message(
                phone="1155551234",
                content="Test message",
                message_type="text",
                wa_message_id="wamid.test123",
                contact_name="Test User",
                channel="whatsapp",
            )

            # channel=whatsapp SÍ llama a WhatsApp
            mock_mark_read.assert_called_once_with("wamid.test123")
            mock_send_text.assert_called_once()

            assert result == "Hola, soy Sofia"

    @pytest.mark.asyncio
    async def test_tool_call_callback_invoked(self):
        """tool_call_callback se invoca cuando se ejecuta un tool."""
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        callback_data = []

        async def test_callback(data: dict):
            callback_data.append(data)

        manager = ConversationManager(mock_db, MagicMock(), tool_call_callback=test_callback)
        manager._current_conversation_id = 1

        # Mock un tool handler
        with patch.object(manager, "_tool_buscar_paciente", new_callable=AsyncMock, return_value={"status": "not_found"}), \
             patch.object(manager, "_save_tool_call_to_db", new_callable=AsyncMock):

            result = await manager._execute_tool("buscar_paciente", {"telefono": "1155551234"})

        assert result == {"status": "not_found"}
        assert len(callback_data) == 1
        assert callback_data[0]["tool_name"] == "buscar_paciente"
        assert "duration_ms" in callback_data[0]

    @pytest.mark.asyncio
    async def test_tool_call_callback_not_invoked_when_none(self):
        """Sin callback, _execute_tool funciona normalmente."""
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        manager = ConversationManager(mock_db, MagicMock(), tool_call_callback=None)
        manager._current_conversation_id = 1

        with patch.object(manager, "_tool_buscar_paciente", new_callable=AsyncMock, return_value={"status": "found", "paciente": {}}), \
             patch.object(manager, "_save_tool_call_to_db", new_callable=AsyncMock):

            result = await manager._execute_tool("buscar_paciente", {"telefono": "1155551234"})

        assert result["status"] == "found"

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Tool desconocida retorna error sin romper."""
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        manager = ConversationManager(mock_db, MagicMock())
        manager._current_conversation_id = 1

        with patch.object(manager, "_save_tool_call_to_db", new_callable=AsyncMock):
            result = await manager._execute_tool("tool_inexistente", {})

        assert result["status"] == "error"
        assert "desconocida" in result["error"]

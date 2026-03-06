"""Tests para Claude AI client — system prompt, text extraction, tool calling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.claude_ai import (
    _build_system_prompt,
    _extract_text,
    generate_response,
)


class TestBuildSystemPrompt:
    def test_base_prompt_loads(self):
        prompt = _build_system_prompt()
        assert len(prompt) > 50000
        assert "Sofia" in prompt or "SOFIA" in prompt or "Sofía" in prompt

    def test_with_patient_context(self):
        ctx = {
            "telefono": "1123266671",
            "tipo_contacto": "paciente",
            "paciente_nombre": "Juan Pérez",
        }
        prompt = _build_system_prompt(ctx)
        assert "CONTEXTO DEL CONTACTO ACTUAL" in prompt
        assert "Juan Pérez" in prompt

    def test_without_patient_context_none(self):
        prompt = _build_system_prompt(None)
        assert "CONTEXTO DEL CONTACTO ACTUAL" not in prompt

    def test_without_patient_context_empty(self):
        prompt = _build_system_prompt({})
        assert "CONTEXTO DEL CONTACTO ACTUAL" not in prompt


class TestExtractText:
    def test_single_text_block(self):
        response = MagicMock()
        block = MagicMock()
        block.text = "Hola! Soy Sofia"
        block.type = "text"
        response.content = [block]
        assert _extract_text(response) == "Hola! Soy Sofia"

    def test_ignores_tool_use_blocks(self):
        response = MagicMock()
        tool_block = MagicMock(spec=["type", "name", "input", "id"])
        tool_block.type = "tool_use"
        text_block = MagicMock()
        text_block.text = "Resultado"
        text_block.type = "text"
        response.content = [tool_block, text_block]
        assert _extract_text(response) == "Resultado"

    def test_empty_content(self):
        response = MagicMock()
        response.content = []
        assert _extract_text(response) == ""

    def test_multiple_text_blocks(self):
        response = MagicMock()
        b1 = MagicMock()
        b1.text = "Parte 1"
        b2 = MagicMock()
        b2.text = "Parte 2"
        response.content = [b1, b2]
        result = _extract_text(response)
        assert "Parte 1" in result
        assert "Parte 2" in result


class TestGenerateResponseMocked:
    async def test_simple_response_no_tools(self):
        """Respuesta simple sin tool calling."""
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        text_block = MagicMock()
        text_block.text = "Hola! Soy Sofia de STICK"
        text_block.type = "text"
        mock_response.content = [text_block]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=20)

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch("src.clients.claude_ai._get_client", return_value=mock_client):
            result = await generate_response(
                messages=[{"role": "user", "content": "Hola"}],
            )
        assert "Sofia" in result or "STICK" in result

    async def test_tool_calling_loop(self):
        """Claude llama una tool, recibe resultado, y responde."""
        # Primera respuesta: tool_use
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "buscar_paciente"
        tool_block.input = {"telefono": "1123266671"}
        tool_block.id = "tool_abc123"

        tool_response = MagicMock()
        tool_response.stop_reason = "tool_use"
        tool_response.content = [tool_block]
        tool_response.usage = MagicMock(input_tokens=100, output_tokens=20)

        # Segunda respuesta: texto final
        text_block = MagicMock()
        text_block.text = "Encontré al paciente Juan"
        text_block.type = "text"

        text_response = MagicMock()
        text_response.stop_reason = "end_turn"
        text_response.content = [text_block]
        text_response.usage = MagicMock(input_tokens=200, output_tokens=30)

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=[tool_response, text_response]
        )

        tool_executor = AsyncMock(
            return_value={"status": "found", "paciente": {"Nombre": "Juan"}}
        )

        with patch("src.clients.claude_ai._get_client", return_value=mock_client):
            result = await generate_response(
                messages=[{"role": "user", "content": "Buscar paciente"}],
                tool_executor=tool_executor,
            )

        assert result == "Encontré al paciente Juan"
        tool_executor.assert_called_once_with(
            "buscar_paciente", {"telefono": "1123266671"}
        )

    async def test_api_error_returns_fallback(self):
        """Error de API retorna mensaje amigable."""
        import anthropic

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APIError(
                message="Rate limit",
                request=MagicMock(),
                body=None,
            )
        )

        with patch("src.clients.claude_ai._get_client", return_value=mock_client):
            result = await generate_response(
                messages=[{"role": "user", "content": "Hola"}],
            )
        assert "problema técnico" in result or "repetirme" in result

    async def test_tool_execution_error_handled(self):
        """Error en ejecución de tool se reporta a Claude como error."""
        # Primera respuesta: tool_use
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "buscar_paciente"
        tool_block.input = {"telefono": "1111111111"}
        tool_block.id = "tool_err"

        tool_response = MagicMock()
        tool_response.stop_reason = "tool_use"
        tool_response.content = [tool_block]
        tool_response.usage = MagicMock(input_tokens=100, output_tokens=20)

        # Segunda respuesta: texto final tras el error
        text_block = MagicMock()
        text_block.text = "Hubo un error buscando"
        text_block.type = "text"

        text_response = MagicMock()
        text_response.stop_reason = "end_turn"
        text_response.content = [text_block]
        text_response.usage = MagicMock(input_tokens=200, output_tokens=30)

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=[tool_response, text_response]
        )

        tool_executor = AsyncMock(side_effect=Exception("AppSheet timeout"))

        with patch("src.clients.claude_ai._get_client", return_value=mock_client):
            result = await generate_response(
                messages=[{"role": "user", "content": "Buscar"}],
                tool_executor=tool_executor,
            )

        assert result == "Hubo un error buscando"
        # Claude recibió el tool_result con is_error=True
        call_args = mock_client.messages.create.call_args_list[1]
        user_msg = call_args[1]["messages"][-1]
        assert user_msg["role"] == "user"
        assert user_msg["content"][0]["is_error"] is True

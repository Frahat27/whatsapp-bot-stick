"""
Cliente Claude AI (Anthropic) — Integración con Tool Calling.

Flujo:
1. Recibe historial de mensajes + contexto del paciente
2. Llama a Claude con system prompt + tools
3. Si Claude responde con tool_use → ejecuta la tool → envía resultado → loop
4. Cuando Claude responde con texto → retorna la respuesta final

El tool_executor es inyectado desde conversation_manager (patrón callback).
"""

import json
from typing import Any, Callable, Awaitable, Optional

import anthropic

from src.config import get_settings
from src.tools.definitions import ALL_TOOLS
from src.utils.data_loader import build_full_system_prompt
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Tipo del callback que ejecuta tools
ToolExecutor = Callable[[str, dict], Awaitable[Any]]

# Modelo por defecto (se sobreescribe desde config/env CLAUDE_MODEL)
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# Máximo de iteraciones de tool calling (safety net)
MAX_TOOL_ITERATIONS = 15

# Cliente Anthropic (lazy init)
_client: Optional[anthropic.AsyncAnthropic] = None


def _get_client() -> anthropic.AsyncAnthropic:
    """Obtiene o crea el cliente async de Anthropic."""
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY no configurada en .env")
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def close_client() -> None:
    """Cierra el cliente Anthropic (llamar en shutdown)."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


def _build_system_prompt(patient_context: Optional[dict] = None) -> str:
    """
    Construye el system prompt completo.
    Si hay contexto de paciente, lo inyecta al inicio para que Claude
    sepa con quién está hablando.
    Siempre inyecta fecha/hora actual de Argentina.
    """
    from src.utils.dates import now_argentina

    base_prompt = build_full_system_prompt()

    # Siempre inyectar fecha/hora actual
    ahora = now_argentina()
    DIAS_ES = {
        0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves",
        4: "viernes", 5: "sábado", 6: "domingo",
    }
    dia_semana = DIAS_ES[ahora.weekday()]
    fecha_hora_str = ahora.strftime(f"{dia_semana} %d/%m/%Y %H:%M")

    ctx_lines = [
        "\n\n---\n\n# CONTEXTO DE ESTA INTERACCIÓN\n",
        f"- **Fecha y hora actual:** {fecha_hora_str}",
    ]

    if patient_context:
        ctx_lines.append("\n# CONTEXTO DEL CONTACTO ACTUAL\n")
        for key, value in patient_context.items():
            if value:
                ctx_lines.append(f"- **{key}:** {value}")

    context_block = "\n".join(ctx_lines)
    return base_prompt + context_block


async def generate_response(
    messages: list[dict],
    tool_executor: Optional[ToolExecutor] = None,
    patient_context: Optional[dict] = None,
    model: Optional[str] = None,
    max_tokens: int = 1024,
) -> str:
    """
    Genera una respuesta de Claude con tool calling loop + timeout global.

    Args:
        messages: Historial de conversación en formato Anthropic
                  [{"role": "user"|"assistant", "content": "..."}]
        tool_executor: Callback async que ejecuta una tool:
                       async def executor(tool_name, tool_input) -> result
        patient_context: Datos del paciente para inyectar en system prompt
        model: Modelo a usar
        max_tokens: Máximo de tokens por respuesta

    Returns:
        Texto de respuesta final de Claude para enviar al paciente.
    """
    import asyncio

    settings = get_settings()
    timeout = settings.conversation_timeout_seconds
    resolved_model = model or settings.claude_model or DEFAULT_MODEL

    try:
        return await asyncio.wait_for(
            _generate_response_inner(
                messages=messages,
                tool_executor=tool_executor,
                patient_context=patient_context,
                model=resolved_model,
                max_tokens=max_tokens,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "claude_timeout",
            timeout_seconds=timeout,
            messages_count=len(messages),
        )
        return (
            "Dame un momento, estoy consultando tu información. "
            "Ya te respondo."
        )


async def _generate_response_inner(
    messages: list[dict],
    tool_executor: Optional[ToolExecutor] = None,
    patient_context: Optional[dict] = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
) -> str:
    """Lógica interna de generación de respuesta (sin timeout)."""
    client = _get_client()
    system_prompt = _build_system_prompt(patient_context)

    # Copiar mensajes para no mutar el original
    conversation = list(messages)

    # Tools solo si hay executor
    tools = ALL_TOOLS if tool_executor else []

    logger.info(
        "claude_generate_start",
        messages_count=len(conversation),
        has_tools=bool(tools),
        has_patient_context=bool(patient_context),
        model=model,
    )

    for iteration in range(MAX_TOOL_ITERATIONS):
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=conversation,
                tools=tools if tools else anthropic.NOT_GIVEN,
            )
        except anthropic.APIError as e:
            logger.error("claude_api_error", error=str(e), iteration=iteration)
            return "Disculpá, tuve un problema técnico. ¿Podés repetirme tu consulta?"

        logger.debug(
            "claude_response",
            stop_reason=response.stop_reason,
            usage_input=response.usage.input_tokens,
            usage_output=response.usage.output_tokens,
            iteration=iteration,
        )

        # --- Caso 1: Respuesta final (end_turn o sin tools) ---
        if response.stop_reason == "end_turn" or response.stop_reason != "tool_use":
            return _extract_text(response)

        # --- Caso 2: Tool use ---
        if not tool_executor:
            # No hay executor → retornar el texto que haya
            return _extract_text(response)

        # Procesar todas las tool calls en esta respuesta
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                logger.info(
                    "claude_tool_call",
                    tool=tool_name,
                    input_keys=list(tool_input.keys()),
                    iteration=iteration,
                )

                # Ejecutar la tool
                try:
                    result = await tool_executor(tool_name, tool_input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })
                    logger.info(
                        "claude_tool_result",
                        tool=tool_name,
                        status=result.get("status", "ok") if isinstance(result, dict) else "ok",
                    )
                except Exception as e:
                    logger.error(
                        "claude_tool_error",
                        tool=tool_name,
                        error=str(e),
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(
                            {"status": "error", "error": str(e)},
                            ensure_ascii=False,
                        ),
                        "is_error": True,
                    })

        # Agregar la respuesta del assistant (con tool_use) y los resultados
        conversation.append({"role": "assistant", "content": response.content})
        conversation.append({"role": "user", "content": tool_results})

    # Safety net: si llegamos al máximo de iteraciones
    logger.warning("claude_max_iterations", iterations=MAX_TOOL_ITERATIONS)
    return (
        "Disculpá, me llevó más tiempo del esperado procesar tu consulta. "
        "¿Podés reformular tu pregunta?"
    )


async def generate_response_with_image(
    messages: list[dict],
    image_data: bytes,
    media_type: str = "image/jpeg",
    tool_executor: Optional[ToolExecutor] = None,
    patient_context: Optional[dict] = None,
) -> str:
    """
    Genera respuesta de Claude con una imagen (Vision).
    Usado para leer comprobantes de pago.

    Args:
        messages: Historial de conversación
        image_data: Bytes de la imagen
        media_type: Tipo MIME (image/jpeg, image/png, etc.)
        tool_executor: Callback de ejecución de tools
        patient_context: Contexto del paciente
    """
    import base64

    # Construir el mensaje con la imagen
    image_b64 = base64.standard_b64encode(image_data).decode("utf-8")

    image_message = {
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_b64,
                },
            },
            {
                "type": "text",
                "text": (
                    "El paciente envió esta imagen. "
                    "Si es un comprobante de transferencia, extraé: monto, fecha y número de operación. "
                    "Si es una foto de alineadores o dientes, describí lo que ves. "
                    "Si es otra cosa, describila brevemente."
                ),
            },
        ],
    }

    # Agregar la imagen al historial
    full_messages = list(messages) + [image_message]

    return await generate_response(
        messages=full_messages,
        tool_executor=tool_executor,
        patient_context=patient_context,
    )


def _extract_text(response) -> str:
    """Extrae el texto de la respuesta de Claude (ignora tool_use blocks)."""
    text_parts = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
    return "\n".join(text_parts) if text_parts else ""

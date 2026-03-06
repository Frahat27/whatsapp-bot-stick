"""
Conversation Manager — orquestador central del bot Sofía.

Flujo de un mensaje entrante:
1. Buscar/crear conversación en DB por teléfono
2. Check dedup (wa_message_id)
3. Guardar mensaje entrante en DB
4. Check estado (bot_active vs escalated vs admin_takeover)
5. Identificar contacto (paciente → lead → nuevo → admin) via AppSheet
6. Construir historial para Claude
7. Generar respuesta con Claude (tool calling loop)
8. Guardar respuesta en DB
9. Enviar respuesta por WhatsApp
10. Marcar mensaje como leído
"""

import json
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.appsheet import AppSheetClient, get_appsheet_client
from src.clients.claude_ai import generate_response, generate_response_with_image
from src.clients.google_sheets import add_pending_task
from src.clients.whatsapp import send_text, mark_as_read, download_media
from src.config import get_settings
from src.models.conversation import Conversation, ContactType
from src.models.message import Message, MessageRole, MessageType
from src.models.conversation_state import ConversationState, ConversationStatus
from src.utils.dates import to_appsheet_date, today_argentina
from src.utils.logging_config import get_logger
from src.utils.phone import normalize_phone, is_admin_phone, to_whatsapp_format

logger = get_logger(__name__)


class ConversationManager:
    """
    Orquestador central.
    Recibe un mensaje, lo procesa, y devuelve una respuesta.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.appsheet: AppSheetClient = get_appsheet_client()

    # =========================================================================
    # PUNTO DE ENTRADA PRINCIPAL
    # =========================================================================

    async def handle_incoming_message(
        self,
        phone: str,
        content: str,
        message_type: str = "text",
        wa_message_id: Optional[str] = None,
        contact_name: Optional[str] = None,
        media_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Punto de entrada principal para un mensaje entrante.

        Args:
            phone: Teléfono normalizado (10 dígitos)
            content: Contenido del mensaje
            message_type: text, image, audio, etc.
            wa_message_id: ID de WhatsApp para dedup
            contact_name: Nombre del perfil de WhatsApp
            media_id: ID de media de WhatsApp (para imágenes, docs)

        Returns:
            Texto de respuesta o None si no debe responder.
        """
        logger.info(
            "handling_incoming_message",
            phone=phone,
            type=message_type,
            content_preview=content[:80],
        )

        # 1. Buscar o crear conversación
        conversation = await self._get_or_create_conversation(phone)

        # 2. Check dedup (wa_message_id)
        if wa_message_id:
            is_dup = await self._check_duplicate(wa_message_id)
            if is_dup:
                logger.warning("duplicate_message", wa_id=wa_message_id)
                return None

        # 3. Guardar mensaje entrante
        msg_type = self._parse_message_type(message_type)
        await self._save_message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=content,
            message_type=msg_type,
            wa_message_id=wa_message_id,
        )

        # 4. Refrescar mensajes para que el historial incluya el recién guardado
        await self.db.refresh(conversation, attribute_names=["messages"])

        # 5. Marcar como leído
        if wa_message_id:
            await mark_as_read(wa_message_id)

        # 6. Check estado de la conversación
        state = conversation.state
        if state and state.status != ConversationStatus.BOT_ACTIVE:
            logger.info(
                "conversation_not_bot_active",
                status=state.status.value,
                phone=phone,
            )
            return None

        # 6. Detectar admin
        is_admin = is_admin_phone(phone, self.settings.admin_phone_list)
        if is_admin:
            logger.info("admin_message_detected", phone=phone)

        # 7. Identificar contacto via AppSheet
        patient_context = await self._identify_contact(conversation, phone, contact_name)

        # 8. Construir historial para Claude
        messages = self._build_message_history(conversation)

        # 9. Generar respuesta con Claude
        if message_type == "image" and media_id:
            response_text = await self._handle_image_message(
                messages, media_id, patient_context
            )
        else:
            response_text = await generate_response(
                messages=messages,
                tool_executor=self._execute_tool,
                patient_context=patient_context,
            )

        if not response_text:
            logger.warning("empty_response", phone=phone)
            return None

        # 10. Guardar respuesta en DB
        await self._save_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_text,
        )
        await self.db.commit()

        # 11. Enviar por WhatsApp
        wa_phone = to_whatsapp_format(phone)
        await send_text(to=wa_phone, text=response_text)

        logger.info(
            "response_sent",
            phone=phone,
            response_length=len(response_text),
        )
        return response_text

    # =========================================================================
    # IDENTIFICACIÓN DE CONTACTO
    # =========================================================================

    async def _identify_contact(
        self,
        conversation: Conversation,
        phone: str,
        contact_name: Optional[str] = None,
    ) -> dict:
        """
        Identifica al contacto y construye el contexto para Claude.
        Orden: Paciente → Lead → Nuevo → Admin.
        """
        context = {
            "telefono": phone,
            "nombre_whatsapp": contact_name or "",
            "es_admin": is_admin_phone(phone, self.settings.admin_phone_list),
        }

        # Si ya está identificado en la conversación, usar eso
        if conversation.contact_type == ContactType.PACIENTE and conversation.patient_id:
            context["tipo_contacto"] = "paciente"
            context["paciente_id"] = conversation.patient_id
            context["paciente_nombre"] = conversation.patient_name or ""
            return context

        if conversation.contact_type == ContactType.ADMIN:
            context["tipo_contacto"] = "admin"
            return context

        # Admin check
        if context["es_admin"]:
            conversation.contact_type = ContactType.ADMIN
            await self.db.flush()
            context["tipo_contacto"] = "admin"
            return context

        # Buscar en AppSheet
        try:
            # Primero buscar como paciente
            paciente = await self.appsheet.find_patient_by_phone(phone)
            if paciente:
                conversation.contact_type = ContactType.PACIENTE
                conversation.patient_id = paciente.get("_RowNumber", paciente.get("ID", ""))
                conversation.patient_name = paciente.get("Nombre", "")
                await self.db.flush()

                context["tipo_contacto"] = "paciente"
                context["paciente_id"] = conversation.patient_id
                context["paciente_nombre"] = conversation.patient_name
                context["datos_paciente"] = _safe_patient_summary(paciente)
                return context

            # Buscar como lead
            lead = await self.appsheet.find_lead_by_phone(phone)
            if lead:
                conversation.contact_type = ContactType.LEAD
                conversation.lead_id = lead.get("_RowNumber", lead.get("ID", ""))
                conversation.patient_name = lead.get("Nombre", "")
                await self.db.flush()

                context["tipo_contacto"] = "lead"
                context["lead_id"] = conversation.lead_id
                context["lead_nombre"] = conversation.patient_name
                return context

        except Exception as e:
            logger.error("identify_contact_error", error=str(e), phone=phone)

        # No encontrado → contacto nuevo
        context["tipo_contacto"] = "nuevo"
        return context

    # =========================================================================
    # HISTORIAL DE MENSAJES
    # =========================================================================

    def _build_message_history(self, conversation: Conversation) -> list[dict]:
        """
        Construye el historial de mensajes en formato Anthropic.
        Toma los últimos N mensajes configurados.
        """
        limit = self.settings.conversation_history_limit
        recent_messages = conversation.messages[-limit:] if conversation.messages else []

        history = []
        for msg in recent_messages:
            if msg.role == MessageRole.SYSTEM:
                continue
            history.append({
                "role": msg.role.value,
                "content": msg.content,
            })

        # Anthropic requiere que el primer mensaje sea del user
        if history and history[0]["role"] != "user":
            history = history[1:]

        # Asegurar alternancia user/assistant (Anthropic lo requiere)
        history = _ensure_alternation(history)

        return history

    # =========================================================================
    # MANEJO DE IMÁGENES
    # =========================================================================

    async def _handle_image_message(
        self,
        messages: list[dict],
        media_id: str,
        patient_context: dict,
    ) -> str:
        """Descarga la imagen y la envía a Claude Vision."""
        image_data = await download_media(media_id)
        if not image_data:
            return (
                "Recibí tu imagen pero no pude procesarla. "
                "¿Podés enviarla de nuevo?"
            )

        return await generate_response_with_image(
            messages=messages,
            image_data=image_data,
            tool_executor=self._execute_tool,
            patient_context=patient_context,
        )

    # =========================================================================
    # TOOL EXECUTOR — Dispatch a AppSheet / Google Sheets
    # =========================================================================

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """
        Ejecuta una tool solicitada por Claude.
        Dispatcher central que routea a AppSheet, Google Sheets, etc.
        """
        logger.info("tool_execute", tool=tool_name)

        handlers = {
            "buscar_paciente": self._tool_buscar_paciente,
            "buscar_lead": self._tool_buscar_lead,
            "crear_lead": self._tool_crear_lead,
            "crear_paciente": self._tool_crear_paciente,
            "consultar_horarios": self._tool_consultar_horarios,
            "buscar_disponibilidad": self._tool_buscar_disponibilidad,
            "agendar_turno": self._tool_agendar_turno,
            "buscar_turno_paciente": self._tool_buscar_turno_paciente,
            "modificar_turno": self._tool_modificar_turno,
            "cancelar_turno": self._tool_cancelar_turno,
            "consultar_tarifario": self._tool_consultar_tarifario,
            "consultar_presupuesto": self._tool_consultar_presupuesto,
            "buscar_pago": self._tool_buscar_pago,
            "registrar_pago": self._tool_registrar_pago,
            "crear_tarea_pendiente": self._tool_crear_tarea_pendiente,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"status": "error", "error": f"Tool desconocida: {tool_name}"}

        try:
            return await handler(tool_input)
        except Exception as e:
            logger.error("tool_execution_error", tool=tool_name, error=str(e))
            return {"status": "error", "error": str(e)}

    # --- Tool handlers ---

    async def _tool_buscar_paciente(self, inp: dict) -> dict:
        telefono = inp["telefono"]
        paciente = await self.appsheet.find_patient_by_phone(telefono)
        if paciente:
            return {"status": "found", "paciente": paciente}
        return {"status": "not_found"}

    async def _tool_buscar_lead(self, inp: dict) -> dict:
        telefono = inp["telefono"]
        lead = await self.appsheet.find_lead_by_phone(telefono)
        if lead:
            return {"status": "found", "lead": lead}
        return {"status": "not_found"}

    async def _tool_crear_lead(self, inp: dict) -> dict:
        row = {
            "Nombre": inp["nombre"],
            "Telefono (Whatsapp)": inp["telefono"],
            "Canal": inp.get("canal", "WhatsApp"),
            "Motivo": inp.get("motivo", ""),
            "Estado Lead": "Abierta",
        }
        result = await self.appsheet.add("BBDD LEADS", [row])
        return {"status": "created", "lead": result[0] if result else row}

    async def _tool_crear_paciente(self, inp: dict) -> dict:
        from src.utils.dates import to_appsheet_date
        from datetime import datetime

        # Parsear fecha de nacimiento DD/MM/YYYY → MM/DD/YYYY
        fecha_nac = inp["fecha_nacimiento"]
        try:
            dt = datetime.strptime(fecha_nac, "%d/%m/%Y")
            fecha_appsheet = to_appsheet_date(dt.date())
        except ValueError:
            fecha_appsheet = fecha_nac

        row = {
            "Nombre": inp["nombre"],
            "DNI / Pasaporte": inp["dni"],
            "Fecha Nacimiento": fecha_appsheet,
            "Telefono (Whatsapp)": inp["telefono"],
            "Email": inp["mail"],
            "Referido": inp.get("referido_por", ""),
        }
        result = await self.appsheet.add("BBDD PACIENTES", [row])
        return {"status": "created", "paciente": result[0] if result else row}

    async def _tool_consultar_horarios(self, inp: dict) -> dict:
        horarios = await self.appsheet.find("LISTA O | HORARIOS DE ATENCION")
        return {"status": "ok", "horarios": horarios}

    async def _tool_buscar_disponibilidad(self, inp: dict) -> dict:
        """
        Busca disponibilidad cruzando horarios con turnos existentes.
        Retorna los turnos ocupados y los horarios de atención para que
        Claude calcule las opciones libres.
        """
        from datetime import timedelta

        semanas = inp.get("semanas", 3)
        hoy = today_argentina()
        fecha_hasta = hoy + timedelta(weeks=semanas)

        # Obtener turnos ocupados en el rango
        selector = (
            f'Filter("BBDD SESIONES", '
            f'AND([Fecha] >= "{to_appsheet_date(hoy)}", '
            f'[Fecha] <= "{to_appsheet_date(fecha_hasta)}", '
            f'OR([Estado Sesion] = "Planificada", [Estado Sesion] = "Confirmada")))'
        )
        turnos_ocupados = await self.appsheet.find("BBDD SESIONES", selector=selector)

        # Obtener horarios de atención
        horarios = await self.appsheet.find("LISTA O | HORARIOS DE ATENCION")

        return {
            "status": "ok",
            "fecha_desde": hoy.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
            "turnos_ocupados": turnos_ocupados,
            "horarios_atencion": horarios,
            "preferencia_dia": inp.get("preferencia_dia", "cualquier dia"),
            "preferencia_horario": inp.get("preferencia_horario", "cualquier horario"),
        }

    async def _tool_agendar_turno(self, inp: dict) -> dict:
        from datetime import datetime

        # Parsear fecha DD/MM/YYYY → MM/DD/YYYY
        try:
            dt = datetime.strptime(inp["fecha"], "%d/%m/%Y")
            fecha_appsheet = to_appsheet_date(dt.date())
        except ValueError:
            fecha_appsheet = inp["fecha"]

        row = {
            "Paciente": inp["paciente_id"],
            "Fecha": fecha_appsheet,
            "Hora": inp["hora"] + ":00" if len(inp["hora"]) <= 5 else inp["hora"],
            "Tratamiento": inp["tratamiento"],
            "Profesional": inp["profesional"],
            "Estado Sesion": "Planificada",
            "Observaciones": inp.get("observaciones", ""),
        }
        result = await self.appsheet.add("BBDD SESIONES", [row])
        return {"status": "created", "turno": result[0] if result else row}

    async def _tool_buscar_turno_paciente(self, inp: dict) -> dict:
        paciente_id = inp["paciente_id"]
        selector = (
            f'Filter("BBDD SESIONES", '
            f'AND([Paciente] = "{paciente_id}", '
            f'OR([Estado Sesion] = "Planificada", '
            f'[Estado Sesion] = "Confirmada", '
            f'[Estado Sesion] = "Realizada")))'
        )
        turnos = await self.appsheet.find("BBDD SESIONES", selector=selector)
        return {"status": "ok", "turnos": turnos}

    async def _tool_modificar_turno(self, inp: dict) -> dict:
        from datetime import datetime

        try:
            dt = datetime.strptime(inp["nueva_fecha"], "%d/%m/%Y")
            fecha_appsheet = to_appsheet_date(dt.date())
        except ValueError:
            fecha_appsheet = inp["nueva_fecha"]

        row = {
            "_RowNumber": inp["turno_id"],
            "Fecha": fecha_appsheet,
            "Hora": inp["nueva_hora"] + ":00" if len(inp["nueva_hora"]) <= 5 else inp["nueva_hora"],
            "Profesional": inp["profesional"],
        }
        result = await self.appsheet.edit("BBDD SESIONES", [row])
        return {"status": "modified", "turno": result[0] if result else row}

    async def _tool_cancelar_turno(self, inp: dict) -> dict:
        row = {
            "_RowNumber": inp["turno_id"],
            "Estado Sesion": "Cancelada",
        }
        result = await self.appsheet.edit("BBDD SESIONES", [row])
        return {"status": "cancelled", "turno": result[0] if result else row}

    async def _tool_consultar_tarifario(self, inp: dict) -> dict:
        tratamiento = inp["tratamiento"]
        selector = (
            f'Filter("BBDD TARIFARIO", '
            f'CONTAINS([Tratamiento], "{tratamiento}"))'
        )
        tarifas = await self.appsheet.find("BBDD TARIFARIO", selector=selector)
        if tarifas:
            return {"status": "ok", "tarifas": tarifas}
        return {"status": "not_found", "mensaje": f"No se encontró tarifa para '{tratamiento}'"}

    async def _tool_consultar_presupuesto(self, inp: dict) -> dict:
        paciente_id = inp["paciente_id"]
        selector = (
            f'Filter("BBDD PRESUPUESTOS", '
            f'[Paciente] = "{paciente_id}")'
        )
        presupuestos = await self.appsheet.find("BBDD PRESUPUESTOS", selector=selector)
        return {"status": "ok", "presupuestos": presupuestos}

    async def _tool_buscar_pago(self, inp: dict) -> dict:
        paciente_id = inp["paciente_id"]
        fecha = inp.get("fecha", "")
        monto = inp.get("monto", "")

        # Buscar pagos del paciente
        selector = (
            f'Filter("BBDD PAGOS", '
            f'[ID Paciente] = "{paciente_id}")'
        )
        pagos = await self.appsheet.find("BBDD PAGOS", selector=selector)

        # Filtrar por fecha y monto si se proporcionaron
        if pagos and (fecha or monto):
            filtered = []
            for p in pagos:
                match_fecha = not fecha or fecha in str(p.get("Fecha", ""))
                match_monto = not monto or str(monto) in str(p.get("Monto", ""))
                if match_fecha and match_monto:
                    filtered.append(p)
            if filtered:
                return {"status": "found", "pagos": filtered, "duplicado": True}

        if pagos:
            return {"status": "ok", "pagos": pagos, "duplicado": False}
        return {"status": "not_found", "pagos": [], "duplicado": False}

    async def _tool_registrar_pago(self, inp: dict) -> dict:
        from datetime import datetime

        fecha = inp["fecha"]
        try:
            dt = datetime.strptime(fecha, "%d/%m/%Y")
            fecha_appsheet = to_appsheet_date(dt.date())
        except ValueError:
            fecha_appsheet = fecha

        row = {
            "ID Paciente": inp["paciente_id"],
            "Fecha": fecha_appsheet,
            "Monto": inp["monto"],
            "Metodo de Pago": inp["metodo_pago"],
            "Tipo de Pago": inp["tipo_pago"],
            "Estado del Pago": "Confirmado",
            "Observaciones": inp.get("observaciones", ""),
        }
        result = await self.appsheet.add("BBDD PAGOS", [row])
        return {"status": "created", "pago": result[0] if result else row}

    async def _tool_crear_tarea_pendiente(self, inp: dict) -> dict:
        result = await add_pending_task(
            tipo=inp["tipo"],
            contexto=inp["contexto"],
            paciente=inp.get("paciente", ""),
            telefono=inp.get("telefono", ""),
            paciente_id=inp.get("paciente_id", ""),
            profesional=inp.get("profesional", ""),
            prioridad=inp.get("prioridad", "🟡 Normal"),
        )
        return result

    # =========================================================================
    # HELPERS DE DB
    # =========================================================================

    async def _get_or_create_conversation(self, phone: str) -> Conversation:
        """Buscar conversación existente o crear una nueva."""
        stmt = select(Conversation).where(Conversation.phone == phone)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if conversation is None:
            conversation = Conversation(phone=phone, contact_type=ContactType.NUEVO)
            self.db.add(conversation)

            state = ConversationState(
                conversation=conversation,
                status=ConversationStatus.BOT_ACTIVE,
            )
            self.db.add(state)

            await self.db.flush()
            logger.info("conversation_created", phone=phone, id=conversation.id)

        return conversation

    async def _check_duplicate(self, wa_message_id: str) -> bool:
        """Verificar si un mensaje ya fue procesado (dedup por wa_message_id)."""
        stmt = select(Message.id).where(Message.wa_message_id == wa_message_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _save_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        wa_message_id: Optional[str] = None,
    ) -> Message:
        """Guardar un mensaje en la DB."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_type=message_type,
            wa_message_id=wa_message_id,
        )
        self.db.add(message)
        await self.db.flush()
        return message

    @staticmethod
    def _parse_message_type(message_type: str) -> MessageType:
        """Parsea el tipo de mensaje de WhatsApp a nuestro enum."""
        try:
            return MessageType(message_type)
        except ValueError:
            return MessageType.TEXT


# =============================================================================
# HELPERS
# =============================================================================

def _safe_patient_summary(paciente: dict) -> str:
    """Genera un resumen de los datos del paciente para el contexto de Claude."""
    fields = [
        ("Nombre", "nombre"),
        ("ID", "id"),
        ("DNI / Pasaporte", "dni"),
        ("Email", "email"),
        ("Estado Tratamiento", "estado_tratamiento"),
        ("Tratamiento", "tratamiento"),
        ("CONSGEN FIRMADO", "consentimiento"),
    ]
    parts = []
    for appsheet_key, label in fields:
        val = paciente.get(appsheet_key, "")
        if val and str(val).strip() and str(val) != "COMPLETAR":
            parts.append(f"{label}: {val}")
    return " | ".join(parts) if parts else "Datos limitados"


def _ensure_alternation(messages: list[dict]) -> list[dict]:
    """
    Asegura que los mensajes alternen user/assistant.
    Anthropic requiere estricta alternancia.
    Si hay mensajes consecutivos del mismo rol, los combina.
    """
    if not messages:
        return messages

    result = [messages[0]]
    for msg in messages[1:]:
        if msg["role"] == result[-1]["role"]:
            # Mismo rol consecutivo → combinar contenido
            result[-1]["content"] += "\n" + msg["content"]
        else:
            result.append(msg)

    return result

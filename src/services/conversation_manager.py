"""
Conversation Manager — orquestador central del bot Sofía.

Flujo de un mensaje entrante:
1. Buscar/crear conversación en DB por teléfono
2. Check dedup (wa_message_id)
3. Guardar mensaje entrante en DB
4. Check estado (bot_active vs escalated vs admin_takeover)
5. Identificar contacto (paciente → lead → nuevo) via Cloud SQL
6. Construir historial para Claude
7. Generar respuesta con Claude (tool calling loop)
8. Guardar respuesta en DB
9. Enviar respuesta por WhatsApp
10. Marcar mensaje como leído
"""

import time
from typing import Any, Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.claude_ai import generate_response, generate_response_with_image
from src.clients.google_sheets import add_pending_task
from src.clients.whatsapp import send_text, mark_as_read, download_media
from src.config import get_settings
from src.db.clinic_repository import ClinicRepository
from src.models.conversation import Conversation, ContactType
from src.models.message import Message, MessageRole, MessageType
from src.models.conversation_state import ConversationState, ConversationStatus
from src.utils.dates import today_argentina
from src.utils.logging_config import get_logger
from src.utils.phone import normalize_phone, is_admin_phone, to_whatsapp_format

logger = get_logger(__name__)


class ConversationManager:
    """
    Orquestador central.
    Recibe un mensaje, lo procesa, y devuelve una respuesta.
    """

    def __init__(
        self,
        db: AsyncSession,
        clinic_db: AsyncSession,
        tool_call_callback: Optional[Callable] = None,
    ):
        self.db = db
        self._clinic_db = clinic_db
        self.clinic_repo = ClinicRepository(clinic_db)
        self.settings = get_settings()
        self._tool_call_callback = tool_call_callback
        self._current_conversation_id: Optional[int] = None

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
        channel: str = "whatsapp",
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
            channel: "whatsapp" o "panel" — controla envío/mark_as_read

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
        self._current_conversation_id = conversation.id

        # 2. Check dedup (wa_message_id)
        if wa_message_id:
            is_dup = await self._check_duplicate(wa_message_id)
            if is_dup:
                logger.warning("duplicate_message", wa_id=wa_message_id)
                return None

        # 3. Guardar mensaje entrante
        msg_type = self._parse_message_type(message_type)
        user_msg = await self._save_message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=content,
            message_type=msg_type,
            wa_message_id=wa_message_id,
        )

        # Broadcast a panel admin (WS)
        await self._broadcast_message(conversation.id, user_msg)

        # 4. Refrescar mensajes para que el historial incluya el recién guardado
        await self.db.refresh(conversation, attribute_names=["messages"])

        # 5. Marcar como leído (solo WhatsApp)
        if channel == "whatsapp" and wa_message_id:
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

        # 7. Identificar contacto via Cloud SQL
        patient_context = await self._identify_contact(conversation, phone, contact_name)

        # 8. Construir historial para Claude
        messages = self._build_message_history(conversation)

        # 9. Generar respuesta con Claude
        if message_type == "image" and media_id:
            response_text = await self._handle_image_message(
                messages, media_id, patient_context
            )
        elif message_type == "audio" and media_id:
            response_text = await self._handle_audio_message(
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
        assistant_msg = await self._save_message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_text,
        )
        await self.db.commit()

        # Broadcast respuesta a panel admin (WS)
        await self._broadcast_message(conversation.id, assistant_msg)

        # 11. Enviar por WhatsApp (solo si el canal es WhatsApp)
        if channel == "whatsapp":
            wa_phone = to_whatsapp_format(phone)
            await send_text(to=wa_phone, text=response_text)

        logger.info(
            "response_sent",
            phone=phone,
            channel=channel,
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

        # Buscar en Cloud SQL
        try:
            # Primero buscar como paciente
            paciente = await self.clinic_repo.find_patient_by_phone(phone)
            if paciente:
                conversation.contact_type = ContactType.PACIENTE
                conversation.patient_id = paciente.id_paciente
                conversation.patient_name = paciente.paciente
                await self.db.flush()

                context["tipo_contacto"] = "paciente"
                context["paciente_id"] = conversation.patient_id
                context["paciente_nombre"] = conversation.patient_name
                context["datos_paciente"] = _safe_patient_summary(paciente.to_appsheet_dict())
                context["ya_buscado_en_db"] = True
                context["nota"] = (
                    "Ya se identificó como paciente en la DB. "
                    "NO uses buscar_paciente ni buscar_lead."
                )
                return context

            # Buscar como lead
            lead = await self.clinic_repo.find_lead_by_phone(phone)
            if lead:
                conversation.contact_type = ContactType.LEAD
                conversation.lead_id = lead.id_lead
                conversation.patient_name = lead.nombre
                await self.db.flush()

                context["tipo_contacto"] = "lead"
                context["lead_id"] = conversation.lead_id
                context["lead_nombre"] = conversation.patient_name
                context["ya_buscado_en_db"] = True
                context["nota"] = (
                    "Ya se identificó como lead en la DB. "
                    "NO uses buscar_paciente ni buscar_lead."
                )
                return context

        except Exception as e:
            logger.error("identify_contact_error", error=str(e), phone=phone)

        # No encontrado → contacto nuevo
        context["tipo_contacto"] = "nuevo"
        context["ya_buscado_en_db"] = True
        context["nota"] = (
            "Ya se buscó este teléfono en la DB: NO es paciente ni lead. "
            "NO uses buscar_paciente ni buscar_lead, procedé directo a crear_lead "
            "o a responder según corresponda."
        )
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
    # MANEJO DE AUDIO
    # =========================================================================

    async def _handle_audio_message(
        self,
        messages: list[dict],
        media_id: str,
        patient_context: dict,
    ) -> str:
        """
        Descarga el audio de WhatsApp, lo transcribe con Groq Whisper,
        y envía el texto transcrito a Claude como si el paciente lo hubiera escrito.
        """
        from src.clients.audio_transcription import is_transcription_available, transcribe_audio

        # 1. Verificar que la transcripción esté disponible
        if not is_transcription_available():
            logger.warning("audio_transcription_not_available")
            return (
                "Recibí tu mensaje de voz pero no puedo escucharlo en este momento. "
                "¿Podés escribirme tu consulta por texto?"
            )

        # 2. Descargar audio de WhatsApp
        audio_data = await download_media(media_id)
        if not audio_data:
            logger.error("audio_download_failed", media_id=media_id)
            return (
                "No pude descargar tu audio. "
                "¿Podés enviarlo de nuevo o escribirme por texto?"
            )

        # 3. Transcribir con Groq Whisper
        transcription = await transcribe_audio(audio_data)
        if not transcription:
            logger.warning("audio_transcription_failed", media_id=media_id)
            return (
                "No pude entender tu mensaje de voz. "
                "¿Podés escribirme tu consulta por texto?"
            )

        logger.info(
            "audio_transcribed",
            media_id=media_id,
            text_length=len(transcription),
            text_preview=transcription[:80],
        )

        # 4. Reemplazar "[Audio recibido]" en el historial con el texto transcrito
        audio_text = f"[El paciente envió un audio que dice:] {transcription}"
        if messages and messages[-1]["role"] == "user":
            messages[-1]["content"] = audio_text
        else:
            messages.append({"role": "user", "content": audio_text})

        # 5. Generar respuesta con Claude
        return await generate_response(
            messages=messages,
            tool_executor=self._execute_tool,
            patient_context=patient_context,
        )

    # =========================================================================
    # TOOL EXECUTOR — Dispatch a Cloud SQL / Google Sheets
    # =========================================================================

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """
        Ejecuta una tool solicitada por Claude.
        Dispatcher central que routea a Cloud SQL, Google Sheets, etc.
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

        t0 = time.monotonic()
        try:
            result = await handler(tool_input)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error("tool_execution_error", tool=tool_name, error=str(e), traceback=tb)
            result = {"status": "error", "error": str(e)}

        duration_ms = (time.monotonic() - t0) * 1000

        tool_data = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_result": result,
            "duration_ms": round(duration_ms, 1),
        }

        # Persistir tool call en DB (siempre)
        await self._save_tool_call_to_db(self._current_conversation_id, tool_data)

        # Notificar callback externo (para panel admin simulate)
        if self._tool_call_callback:
            try:
                await self._tool_call_callback(tool_data)
            except Exception as cb_err:
                logger.warning("tool_call_callback_error", error=str(cb_err))

        return result

    # --- Tool handlers ---

    async def _tool_buscar_paciente(self, inp: dict) -> dict:
        telefono = inp["telefono"]
        paciente = await self.clinic_repo.find_patient_by_phone(telefono)
        if paciente:
            return {"status": "found", "paciente": paciente.to_appsheet_dict()}
        return {"status": "not_found"}

    async def _tool_buscar_lead(self, inp: dict) -> dict:
        telefono = inp["telefono"]
        lead = await self.clinic_repo.find_lead_by_phone(telefono)
        if lead:
            return {"status": "found", "lead": lead.to_appsheet_dict()}
        return {"status": "not_found"}

    async def _tool_crear_lead(self, inp: dict) -> dict:
        telefono = inp["telefono"]
        if not telefono.startswith("+"):
            telefono = f"+{to_whatsapp_format(telefono)}"
        lead = await self.clinic_repo.create_lead(
            nombre=inp["nombre"],
            telefono=telefono,
            motivo_interes=inp.get("motivo", ""),
            notas="Primer contacto via WhatsApp bot",
        )
        await self._clinic_db.commit()
        return {"status": "created", "lead": lead.to_appsheet_dict()}

    async def _tool_crear_paciente(self, inp: dict) -> dict:
        from datetime import datetime

        # Parsear fecha de nacimiento DD/MM/YYYY → date
        fecha_nac = inp["fecha_nacimiento"]
        fecha_date = None
        try:
            dt = datetime.strptime(fecha_nac, "%d/%m/%Y")
            fecha_date = dt.date()
        except ValueError:
            pass

        telefono = inp["telefono"]
        if not telefono.startswith("+"):
            telefono = f"+{to_whatsapp_format(telefono)}"

        paciente = await self.clinic_repo.create_patient(
            nombre=inp["nombre"],
            telefono=telefono,
            dni=inp["dni"],
            fecha_nacimiento=fecha_date,
            sexo=inp.get("sexo", "Otro"),
            email=inp["mail"],
            referido=inp.get("referido_por"),
        )
        await self._clinic_db.commit()
        return {"status": "created", "paciente": paciente.to_appsheet_dict()}

    async def _tool_consultar_horarios(self, inp: dict) -> dict:
        horarios = await self.clinic_repo.get_all_horarios()
        return {"status": "ok", "horarios": [h.to_appsheet_dict() for h in horarios]}

    async def _tool_buscar_disponibilidad(self, inp: dict) -> dict:
        """
        Busca disponibilidad cruzando horarios con turnos existentes.
        Calcula slots libres en Python (determinístico) y retorna 2-3 opciones.
        Lee la duración del tratamiento de LISTA A | tipo tratamientos.

        Parámetro opcional fecha_referencia (DD/MM/YYYY): si se pasa, busca
        alrededor de esa fecha (ej: al reprogramar un turno existente).
        """
        from datetime import timedelta

        from src.services.availability import (
            calculate_available_slots,
            format_slots_for_claude,
            get_treatment_duration,
        )

        semanas = inp.get("semanas", 3)
        hoy = today_argentina()
        tratamiento = inp.get("tipo_turno", "Odontología primera vez")

        # Parsear fecha_desde (o fecha_referencia por backward-compat)
        fecha_target_str = (
            inp.get("fecha_desde", "")
            or inp.get("fecha_referencia", "")
        )
        fecha_desde = hoy
        fecha_hasta = hoy + timedelta(weeks=semanas)

        if fecha_target_str:
            from datetime import datetime as dt_cls
            fecha_target = None
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
                try:
                    fecha_target = dt_cls.strptime(fecha_target_str, fmt).date()
                    break
                except ValueError:
                    continue

            if fecha_target:
                # Auto-corrección del año si Claude pasó año incorrecto
                if fecha_target < hoy:
                    corrected = fecha_target.replace(year=hoy.year)
                    if corrected >= hoy:
                        fecha_target = corrected
                    else:
                        corrected = fecha_target.replace(year=hoy.year + 1)
                        if corrected >= hoy:
                            fecha_target = corrected

                if fecha_target >= hoy:
                    fecha_desde = fecha_target
                    fecha_hasta = fecha_target + timedelta(weeks=semanas)

            logger.info(
                "fecha_desde_parsed",
                raw=fecha_target_str,
                parsed=str(fecha_target),
                final_desde=str(fecha_desde),
                final_hasta=str(fecha_hasta),
            )

        # Obtener datos de Cloud SQL y convertir a dicts para availability.py
        try:
            sesiones = await self.clinic_repo.find_sessions_in_range(fecha_desde, fecha_hasta)
            turnos_ocupados = [s.to_appsheet_dict() for s in sesiones]
            logger.info("disponibilidad_query_ok", step="sesiones", count=len(turnos_ocupados))
        except Exception as e:
            logger.error("disponibilidad_query_fail", step="sesiones", error=str(e))
            raise

        try:
            horarios_models = await self.clinic_repo.get_all_horarios()
            horarios = [h.to_appsheet_dict() for h in horarios_models]
            logger.info("disponibilidad_query_ok", step="horarios", count=len(horarios))
        except Exception as e:
            logger.error("disponibilidad_query_fail", step="horarios", error=str(e))
            raise

        try:
            tipos_models = await self.clinic_repo.get_all_treatment_types()
            tipos_tratamiento = [t.to_appsheet_dict() for t in tipos_models]
            logger.info("disponibilidad_query_ok", step="tipos", count=len(tipos_tratamiento))
        except Exception as e:
            logger.error("disponibilidad_query_fail", step="tipos", error=str(e))
            raise

        # ── DEBUG: Log de diagnóstico para availability ──────────
        logger.info(
            "availability_debug",
            fecha_desde=str(fecha_desde),
            fecha_hasta=str(fecha_hasta),
            horarios_count=len(horarios),
            horarios_data=horarios[:3] if horarios else "EMPTY!",
            sesiones_count=len(turnos_ocupados),
            tipos_count=len(tipos_tratamiento),
            tratamiento=tratamiento,
            fecha_target_raw=fecha_target_str if fecha_target_str else "none",
        )
        # ─────────────────────────────────────────────────────────

        # Determinar duración del tratamiento
        duracion = get_treatment_duration(tratamiento, tipos_tratamiento)

        # Calcular slots disponibles (determinístico, en Python)
        slots = calculate_available_slots(
            horarios=horarios,
            turnos_ocupados=turnos_ocupados,
            tratamiento=tratamiento,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            preferencia_dia=inp.get("preferencia_dia", "cualquier dia"),
            preferencia_horario=inp.get("preferencia_horario", "cualquier horario"),
            duracion_minutos=duracion,
        )

        # ── DEBUG: Log resultado ─────────────────────────────────
        logger.info(
            "availability_result",
            slots_found=len(slots),
            slots_preview=[
                f"{s.get('fecha_display')} {s.get('hora')}"
                for s in slots[:5]
            ] if slots else "NO_SLOTS",
            duracion=duracion,
        )
        # ─────────────────────────────────────────────────────────

        if slots:
            return {
                "status": "ok",
                "opciones_disponibles": slots,
                "opciones_texto": format_slots_for_claude(slots),
                "tratamiento": tratamiento,
                "duracion_minutos": duracion,
            }
        return {
            "status": "sin_disponibilidad",
            "mensaje": (
                f"No se encontraron turnos disponibles para {tratamiento} "
                f"en las próximas {semanas} semanas. "
                f"[DEBUG: horarios={len(horarios)}, sesiones={len(turnos_ocupados)}, "
                f"rango={fecha_desde}→{fecha_hasta}]"
            ),
            "tratamiento": tratamiento,
            "duracion_minutos": duracion,
        }

    async def _tool_agendar_turno(self, inp: dict) -> dict:
        from datetime import datetime, time as time_type

        # Parsear fecha DD/MM/YYYY → date
        try:
            dt = datetime.strptime(inp["fecha"], "%d/%m/%Y")
            fecha_date = dt.date()
        except ValueError:
            fecha_date = datetime.strptime(inp["fecha"], "%Y-%m-%d").date()

        # Parsear hora HH:MM → time
        hora_str = inp["hora"]
        try:
            hora_time = datetime.strptime(hora_str, "%H:%M").time()
        except ValueError:
            hora_time = time_type(9, 0)

        sesion = await self.clinic_repo.create_session(
            id_paciente=inp["paciente_id"],
            paciente_nombre=inp["paciente_nombre"],
            tratamiento=inp["tratamiento"],
            fecha=fecha_date,
            hora=hora_time,
            profesional=inp["profesional"],
            duracion_minutos=inp.get("duracion_minutos", 30),
            descripcion=inp.get("observaciones", ""),
        )
        await self._clinic_db.commit()
        return {"status": "created", "turno": sesion.to_appsheet_dict()}

    async def _tool_buscar_turno_paciente(self, inp: dict) -> dict:
        paciente_id = inp["paciente_id"]
        turnos = await self.clinic_repo.find_patient_active_sessions(paciente_id)
        # Enriquecer con día de semana para evitar que Claude lo calcule mal
        DIAS_ES = {0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves",
                   4: "viernes", 5: "sábado", 6: "domingo"}
        result = []
        for t in turnos:
            d = t.to_appsheet_dict()
            if t.fecha:
                d["Dia de Semana"] = DIAS_ES.get(t.fecha.weekday(), "")
            result.append(d)
        return {"status": "ok", "turnos": result}

    async def _tool_modificar_turno(self, inp: dict) -> dict:
        from datetime import datetime

        # Parsear nueva fecha DD/MM/YYYY → date
        try:
            dt = datetime.strptime(inp["nueva_fecha"], "%d/%m/%Y")
            nueva_fecha = dt.date()
        except ValueError:
            nueva_fecha = datetime.strptime(inp["nueva_fecha"], "%Y-%m-%d").date()

        # Parsear nueva hora HH:MM → time
        try:
            nueva_hora = datetime.strptime(inp["nueva_hora"], "%H:%M").time()
        except ValueError:
            nueva_hora = None

        update_data = {"fecha": nueva_fecha, "profesional": inp["profesional"]}
        if nueva_hora:
            update_data["hora"] = nueva_hora

        sesion = await self.clinic_repo.update_session(inp["turno_id"], **update_data)
        await self._clinic_db.commit()
        if sesion:
            return {"status": "modified", "turno": sesion.to_appsheet_dict()}
        return {"status": "error", "error": f"Turno {inp['turno_id']} no encontrado"}

    async def _tool_cancelar_turno(self, inp: dict) -> dict:
        sesion = await self.clinic_repo.update_session(inp["turno_id"], estado="Cancelada")
        await self._clinic_db.commit()
        if sesion:
            return {"status": "cancelled", "turno": sesion.to_appsheet_dict()}
        return {"status": "error", "error": f"Turno {inp['turno_id']} no encontrado"}

    async def _tool_consultar_tarifario(self, inp: dict) -> dict:
        tratamiento = inp["tratamiento"]
        try:
            tarifa = await self.clinic_repo.find_tariff(tratamiento)
            if tarifa:
                return {"status": "ok", "tarifas": [tarifa.to_appsheet_dict()]}
            # Si no encontró exacta, retornar todas para que Claude elija
            all_tarifas = await self.clinic_repo.find_all_tariffs()
            if all_tarifas:
                return {"status": "ok", "tarifas": [t.to_appsheet_dict() for t in all_tarifas]}
            return {"status": "not_found", "mensaje": f"No se encontró tarifa para '{tratamiento}'"}
        except Exception as model_err:
            # Model query failed — rollback and use raw SQL fallback
            import traceback
            logger.error(
                "tarifario_model_error",
                error=str(model_err),
                traceback=traceback.format_exc(),
            )
            await self._clinic_db.rollback()

            # Diagnostic: log actual table columns
            try:
                cols = await self.clinic_repo.diagnose_tarifario_columns()
                logger.warning("tarifario_actual_columns", columns=cols)
            except Exception as diag_err:
                logger.error("tarifario_diag_error", error=str(diag_err))
                await self._clinic_db.rollback()

            # Raw SQL fallback
            try:
                rows = await self.clinic_repo.find_tariff_raw(tratamiento)
                if rows:
                    return {"status": "ok", "tarifas": rows}
                all_rows = await self.clinic_repo.find_all_tariffs_raw()
                if all_rows:
                    return {"status": "ok", "tarifas": all_rows}
                return {"status": "not_found", "mensaje": f"No se encontró tarifa para '{tratamiento}'"}
            except Exception as raw_err:
                logger.error("tarifario_raw_error", error=str(raw_err))
                await self._clinic_db.rollback()
                return {"status": "error", "error": f"Error consultando tarifario: {raw_err}"}

    async def _tool_consultar_presupuesto(self, inp: dict) -> dict:
        paciente_id = inp["paciente_id"]
        presupuestos = await self.clinic_repo.find_budgets_by_patient(paciente_id)
        return {"status": "ok", "presupuestos": [p.to_appsheet_dict() for p in presupuestos]}

    async def _tool_buscar_pago(self, inp: dict) -> dict:
        from datetime import datetime
        from decimal import Decimal

        paciente_id = inp["paciente_id"]
        fecha_str = inp.get("fecha", "")
        monto_str = inp.get("monto", "")
        metodo = inp.get("metodo_pago", "")

        # Parsear fecha
        fecha_date = None
        if fecha_str:
            try:
                dt = datetime.strptime(fecha_str, "%d/%m/%Y")
                fecha_date = dt.date()
            except ValueError:
                pass

        # Parsear monto
        monto_decimal = None
        if monto_str:
            try:
                monto_decimal = Decimal(str(monto_str))
            except Exception:
                pass

        pagos = await self.clinic_repo.find_payments(
            patient_id=paciente_id,
            fecha=fecha_date,
            monto=monto_decimal,
            metodo=metodo or None,
        )
        pagos_dicts = [p.to_appsheet_dict() for p in pagos]

        # Si buscaba con fecha+monto y encontró → es duplicado
        duplicado = bool(pagos_dicts and fecha_str and monto_str)
        if pagos_dicts:
            return {"status": "found", "pagos": pagos_dicts, "duplicado": duplicado}
        return {"status": "not_found", "pagos": [], "duplicado": False}

    async def _tool_registrar_pago(self, inp: dict) -> dict:
        from datetime import datetime
        from decimal import Decimal

        fecha_str = inp["fecha"]
        try:
            dt = datetime.strptime(fecha_str, "%d/%m/%Y")
            fecha_date = dt.date()
        except ValueError:
            fecha_date = datetime.strptime(fecha_str, "%Y-%m-%d").date()

        monto = Decimal(str(inp["monto"]))

        pago = await self.clinic_repo.create_payment(
            id_paciente=inp["paciente_id"],
            paciente_nombre=inp["paciente_nombre"],
            tratamiento=inp["tratamiento"],
            fecha=fecha_date,
            monto=monto,
            metodo_pago=inp["metodo_pago"],
            tipo_pago=inp["tipo_pago"],
            moneda=inp.get("moneda", "PESOS"),
            observaciones=inp.get("observaciones", ""),
        )
        await self._clinic_db.commit()
        return {"status": "created", "pago": pago.to_appsheet_dict()}

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
    # WS BROADCAST + TOOL CALL PERSISTENCE
    # =========================================================================

    async def _broadcast_message(self, conversation_id: int, msg: "Message"):
        """Broadcast un mensaje al panel admin via WebSocket."""
        try:
            from src.api.admin_ws import broadcast_new_message
            await broadcast_new_message(
                conversation_id=conversation_id,
                message_id=msg.id,
                role=msg.role.value,
                content=msg.content,
                created_at=msg.created_at,
            )
        except Exception:
            pass  # WS broadcast es best-effort, no debe romper el flujo

    async def _save_tool_call_to_db(self, conversation_id: int, data: dict):
        """Persiste un tool call en la tabla tool_calls."""
        try:
            from src.models.tool_call import ToolCall
            tc = ToolCall(
                conversation_id=conversation_id,
                tool_name=data["tool_name"],
                tool_input=data.get("tool_input", {}),
                tool_result=data.get("tool_result"),
                duration_ms=data.get("duration_ms"),
                status="error" if isinstance(data.get("tool_result"), dict)
                    and data["tool_result"].get("status") == "error" else "success",
            )
            self.db.add(tc)
            await self.db.flush()
        except Exception as e:
            logger.warning("save_tool_call_error", error=str(e))

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
        ("Paciente", "nombre"),
        ("ID Paciente", "id"),
        ("DNI / Pasaporte", "dni"),
        ("email", "email"),
        ("Estado del Paciente", "estado"),
        ("Tratamiento", "tratamiento"),
        ("SALDO PEND", "saldo_pendiente"),
        ("Proximo Turno", "proximo_turno"),
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

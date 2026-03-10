"""
Admin panel REST API endpoints.

Endpoints para el panel admin: listar conversaciones, ver mensajes,
simular pacientes (testing), y controlar estado de conversaciones.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.auth import AdminUser, get_current_admin
from src.api.admin_ws import broadcast_new_message, broadcast_tool_call, broadcast_state_changed
from src.db.clinic_session import get_clinic_db
from src.db.session import get_db
from src.models.conversation import Conversation, ContactType
from src.models.conversation_state import ConversationState, ConversationStatus
from src.models.message import Message, MessageRole
from src.models.tool_call import ToolCall
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin)],
)


# =========================================================================
# SCHEMAS
# =========================================================================

class ConversationListItem(BaseModel):
    id: int
    phone: str
    contact_type: Optional[str]
    patient_name: Optional[str]
    status: str
    last_message_preview: Optional[str]
    last_message_at: Optional[str]
    message_count: int

    model_config = ConfigDict(from_attributes=True)


class ToolCallOut(BaseModel):
    id: int
    tool_name: str
    tool_input: dict
    tool_result: Optional[dict]
    duration_ms: Optional[float]
    status: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    message_type: str
    created_at: str
    tool_calls: list[ToolCallOut] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationDetail(BaseModel):
    id: int
    phone: str
    contact_type: Optional[str]
    patient_id: Optional[str]
    patient_name: Optional[str]
    lead_id: Optional[str]
    is_active: bool
    status: str
    labels: list[str]
    admin_notes: Optional[str]
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class SimulateRequest(BaseModel):
    phone: str
    content: str
    contact_name: Optional[str] = "Panel Test"


class SimulateResponse(BaseModel):
    response_text: Optional[str]
    conversation_id: int
    tool_calls: list[ToolCallOut] = []


class StateUpdateRequest(BaseModel):
    status: Optional[str] = None
    labels: Optional[list[str]] = None
    admin_notes: Optional[str] = None


# =========================================================================
# ENDPOINTS
# =========================================================================

@router.get("/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    status: Optional[str] = None,
    contact_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Lista todas las conversaciones con preview del último mensaje."""
    # Subquery: último mensaje por conversación
    last_msg_subq = (
        select(
            Message.conversation_id,
            func.max(Message.id).label("last_msg_id"),
            func.count(Message.id).label("msg_count"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    # Query principal
    query = (
        select(
            Conversation,
            Message.content.label("last_content"),
            Message.created_at.label("last_at"),
            last_msg_subq.c.msg_count,
        )
        .outerjoin(last_msg_subq, Conversation.id == last_msg_subq.c.conversation_id)
        .outerjoin(Message, Message.id == last_msg_subq.c.last_msg_id)
        .options(selectinload(Conversation.state))
    )

    # Filtros
    if status:
        query = query.where(
            Conversation.state.has(ConversationState.status == status)
        )
    if contact_type:
        query = query.where(Conversation.contact_type == contact_type)
    if search:
        query = query.where(
            or_(
                Conversation.phone.ilike(f"%{search}%"),
                Conversation.patient_name.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(desc("last_at")).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for conv, last_content, last_at, msg_count in rows:
        state = conv.state
        items.append(ConversationListItem(
            id=conv.id,
            phone=conv.phone,
            contact_type=conv.contact_type.value if conv.contact_type else None,
            patient_name=conv.patient_name,
            status=state.status.value if state else "bot_active",
            last_message_preview=(last_content[:80] + "...") if last_content and len(last_content) > 80 else last_content,
            last_message_at=str(last_at) if last_at else None,
            message_count=msg_count or 0,
        ))

    return items


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Detalle de una conversación con estado y datos del contacto."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.state))
        .where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    state = conv.state
    return ConversationDetail(
        id=conv.id,
        phone=conv.phone,
        contact_type=conv.contact_type.value if conv.contact_type else None,
        patient_id=conv.patient_id,
        patient_name=conv.patient_name,
        lead_id=conv.lead_id,
        is_active=conv.is_active,
        status=state.status.value if state else "bot_active",
        labels=state.labels or [] if state else [],
        admin_notes=state.admin_notes if state else None,
        created_at=str(conv.created_at),
        updated_at=str(conv.updated_at),
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def get_messages(
    conversation_id: int,
    limit: int = Query(50, le=200),
    before_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Mensajes de una conversación con tool calls intercalados."""
    # Verificar que existe
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    # Mensajes
    msg_query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
    )
    if before_id:
        msg_query = msg_query.where(Message.id < before_id)
    msg_query = msg_query.order_by(desc(Message.id)).limit(limit)

    msg_result = await db.execute(msg_query)
    messages = list(reversed(msg_result.scalars().all()))

    if not messages:
        return []

    # Tool calls en el rango de tiempo de estos mensajes
    first_ts = messages[0].created_at
    last_ts = messages[-1].created_at
    tc_result = await db.execute(
        select(ToolCall)
        .where(
            ToolCall.conversation_id == conversation_id,
            ToolCall.created_at >= first_ts,
            ToolCall.created_at <= last_ts,
        )
        .order_by(ToolCall.created_at)
    )
    tool_calls = tc_result.scalars().all()

    # Agrupar tool calls por timestamp (asociar al mensaje assistant más cercano posterior)
    tc_by_msg: dict[int, list[ToolCallOut]] = {}
    tc_idx = 0
    for msg in messages:
        if msg.role == MessageRole.ASSISTANT:
            msg_tcs = []
            while tc_idx < len(tool_calls) and tool_calls[tc_idx].created_at <= msg.created_at:
                tc = tool_calls[tc_idx]
                msg_tcs.append(ToolCallOut(
                    id=tc.id,
                    tool_name=tc.tool_name,
                    tool_input=tc.tool_input or {},
                    tool_result=tc.tool_result,
                    duration_ms=tc.duration_ms,
                    status=tc.status,
                    created_at=str(tc.created_at),
                ))
                tc_idx += 1
            tc_by_msg[msg.id] = msg_tcs

    # Construir respuesta
    result = []
    for msg in messages:
        result.append(MessageOut(
            id=msg.id,
            role=msg.role.value,
            content=msg.content,
            message_type=msg.message_type.value if msg.message_type else "text",
            created_at=str(msg.created_at),
            tool_calls=tc_by_msg.get(msg.id, []),
        ))

    return result


@router.post("/simulate", response_model=SimulateResponse)
async def simulate_message(
    req: SimulateRequest,
    db: AsyncSession = Depends(get_db),
    clinic_db: AsyncSession = Depends(get_clinic_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    Core testing endpoint: envía un mensaje como si fuera un paciente.
    El flujo completo se ejecuta (Claude + tools + Cloud SQL) sin tocar WhatsApp.
    """
    from src.services.conversation_manager import ConversationManager

    logger.info("simulate_message", phone=req.phone, admin=admin.username)

    # Recopilar tool calls durante esta interacción
    tool_calls_log: list[dict] = []
    conversation_id_holder: list[int] = []

    async def tool_callback(data: dict):
        tool_calls_log.append(data)
        # Broadcast a WebSocket si tenemos conversation_id
        if conversation_id_holder:
            status = "error" if isinstance(data.get("tool_result"), dict) and data["tool_result"].get("status") == "error" else "success"
            await broadcast_tool_call(
                conversation_id=conversation_id_holder[0],
                tool_name=data["tool_name"],
                tool_input=data["tool_input"],
                tool_result=data.get("tool_result"),
                duration_ms=data.get("duration_ms", 0),
                status=status,
            )

    manager = ConversationManager(db, clinic_db, tool_call_callback=tool_callback)

    # Necesitamos el conversation_id para broadcast — lo obtenemos pre-creando
    conv = await manager._get_or_create_conversation(req.phone)
    conversation_id_holder.append(conv.id)

    response_text = await manager.handle_incoming_message(
        phone=req.phone,
        content=req.content,
        message_type="text",
        wa_message_id=None,
        contact_name=req.contact_name,
        channel="panel",
    )

    await db.commit()

    # Formatear tool calls para respuesta
    tc_out = []
    for i, tc in enumerate(tool_calls_log):
        status = "error" if isinstance(tc.get("tool_result"), dict) and tc["tool_result"].get("status") == "error" else "success"
        tc_out.append(ToolCallOut(
            id=i,  # ID temporal, el real está en DB
            tool_name=tc["tool_name"],
            tool_input=tc["tool_input"],
            tool_result=tc.get("tool_result"),
            duration_ms=tc.get("duration_ms"),
            status=status,
            created_at="",
        ))

    return SimulateResponse(
        response_text=response_text,
        conversation_id=conv.id,
        tool_calls=tc_out,
    )


@router.patch("/conversations/{conversation_id}/state")
async def update_conversation_state(
    conversation_id: int,
    req: StateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Actualizar estado de conversación (takeover, labels, notas)."""
    result = await db.execute(
        select(ConversationState)
        .where(ConversationState.conversation_id == conversation_id)
    )
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    if req.status is not None:
        try:
            state.status = ConversationStatus(req.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Estado inválido: {req.status}")

    if req.labels is not None:
        state.labels = req.labels
    if req.admin_notes is not None:
        state.admin_notes = req.admin_notes

    await db.commit()

    # Broadcast cambio de estado
    if req.status:
        await broadcast_state_changed(conversation_id, req.status)

    logger.info(
        "conversation_state_updated",
        conversation_id=conversation_id,
        admin=admin.username,
        new_status=req.status,
    )
    return {"status": "ok", "conversation_id": conversation_id}


# =========================================================================
# DIAGNOSTICS — Availability Debug
# =========================================================================

@router.get("/diagnostics/availability")
async def diagnostics_availability(
    clinic_db: AsyncSession = Depends(get_clinic_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Diagnóstico rápido: muestra datos de horarios, sesiones y config
    para depurar problemas de cálculo de disponibilidad."""
    from datetime import date, timedelta
    from src.db.clinic_repository import ClinicRepository
    from src.utils.dates import today_argentina

    repo = ClinicRepository(clinic_db)
    hoy = today_argentina()

    # 1. Horarios
    horarios_models = await repo.get_all_horarios()
    horarios = [h.to_appsheet_dict() for h in horarios_models]

    # 2. Tipos de tratamiento
    tipos_models = await repo.get_all_treatment_types()
    tipos = [t.to_appsheet_dict() for t in tipos_models]

    # 3. Sesiones próximas 4 semanas
    fecha_hasta = hoy + timedelta(weeks=4)
    sesiones_models = await repo.find_sessions_in_range(hoy, fecha_hasta)
    sesiones_count = len(sesiones_models)
    sesiones_sample = [
        {
            "fecha": s.fecha.isoformat() if s.fecha else None,
            "hora": s.hora.strftime("%H:%M") if s.hora else None,
            "paciente": s.paciente,
            "estado": s.estado,
        }
        for s in sesiones_models[:10]
    ]

    return {
        "hoy": hoy.isoformat(),
        "rango_busqueda": f"{hoy} → {fecha_hasta}",
        "horarios": {
            "count": len(horarios),
            "data": horarios,
            "CRITICAL": "TABLA VACÍA — sin horarios no hay slots!" if not horarios else "OK",
        },
        "tipos_tratamiento": {
            "count": len(tipos),
            "data": tipos,
        },
        "sesiones_proximas": {
            "count": sesiones_count,
            "sample": sesiones_sample,
        },
    }

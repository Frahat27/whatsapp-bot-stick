"""
WebSocket endpoint para el panel admin — eventos real-time.

Eventos:
- new_message: mensaje nuevo (user o assistant) en una conversación
- tool_call: tool call ejecutada por Claude
- state_changed: cambio de estado de conversación (takeover, etc.)
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt

from src.config import get_settings
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ConnectionManager:
    """Maneja conexiones WebSocket activas de admins."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("ws_admin_connected", count=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("ws_admin_disconnected", count=len(self.active_connections))

    async def broadcast(self, event: dict):
        """Envía evento a todos los admins conectados."""
        if not self.active_connections:
            return
        message = json.dumps(event, default=str, ensure_ascii=False)
        disconnected = []
        for conn in self.active_connections:
            try:
                await conn.send_text(message)
            except Exception:
                disconnected.append(conn)
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


# Singleton
_manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    return _manager


@router.websocket("/api/v1/admin/ws")
async def admin_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket para panel admin. Auth via query param token.
    Mantiene conexión abierta y envía eventos en tiempo real.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if not payload.get("sub"):
            await websocket.close(code=4001, reason="Token inválido")
            return
    except JWTError:
        await websocket.close(code=4001, reason="Token inválido o expirado")
        return

    await _manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        _manager.disconnect(websocket)


async def broadcast_new_message(
    conversation_id: int,
    message_id: int,
    role: str,
    content: str,
    created_at: Any,
):
    """Helper: broadcast de mensaje nuevo."""
    await _manager.broadcast({
        "type": "new_message",
        "conversation_id": conversation_id,
        "message": {
            "id": message_id,
            "role": role,
            "content": content,
            "created_at": str(created_at),
        },
    })


async def broadcast_tool_call(
    conversation_id: int,
    tool_name: str,
    tool_input: dict,
    tool_result: Any,
    duration_ms: float,
    status: str,
):
    """Helper: broadcast de tool call."""
    await _manager.broadcast({
        "type": "tool_call",
        "conversation_id": conversation_id,
        "tool_call": {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_result": tool_result,
            "duration_ms": duration_ms,
            "status": status,
        },
    })


async def broadcast_state_changed(conversation_id: int, status: str):
    """Helper: broadcast de cambio de estado."""
    await _manager.broadcast({
        "type": "state_changed",
        "conversation_id": conversation_id,
        "status": status,
    })

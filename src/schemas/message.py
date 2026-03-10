"""
Pydantic schemas para mensajes internos y respuestas API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class MessageOut(BaseModel):
    """Representación de un mensaje para API responses."""
    id: int
    role: str
    content: str
    message_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationOut(BaseModel):
    """Representación de una conversación para API responses."""
    id: int
    phone: str
    contact_type: str
    patient_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    """Respuesta del endpoint /health."""
    status: str = "ok"
    environment: str
    database: str  # "connected" o "error"
    version: str = "0.1.0"

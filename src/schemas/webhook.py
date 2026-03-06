"""
Pydantic schemas para el payload de WhatsApp Cloud API webhooks.

Referencia: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
"""

from typing import Optional
from pydantic import BaseModel, Field


# --- Incoming webhook payload ---

class WhatsAppProfile(BaseModel):
    name: str


class WhatsAppContact(BaseModel):
    profile: WhatsAppProfile
    wa_id: str


class WhatsAppText(BaseModel):
    body: str


class WhatsAppImage(BaseModel):
    id: str
    mime_type: Optional[str] = None
    sha256: Optional[str] = None
    caption: Optional[str] = None


class WhatsAppAudio(BaseModel):
    id: str
    mime_type: Optional[str] = None


class WhatsAppDocument(BaseModel):
    id: str
    mime_type: Optional[str] = None
    filename: Optional[str] = None
    caption: Optional[str] = None


class WhatsAppLocation(BaseModel):
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None


class WhatsAppMessage(BaseModel):
    """Un mensaje individual de WhatsApp."""
    from_: str = Field(alias="from")  # Teléfono del remitente
    id: str  # wa_message_id para dedup
    timestamp: str
    type: str  # text, image, audio, document, location, sticker, reaction
    text: Optional[WhatsAppText] = None
    image: Optional[WhatsAppImage] = None
    audio: Optional[WhatsAppAudio] = None
    document: Optional[WhatsAppDocument] = None
    location: Optional[WhatsAppLocation] = None

    # WhatsApp usa "from" que es keyword de Python
    model_config = {"populate_by_name": True}


class WhatsAppStatus(BaseModel):
    """Status update de un mensaje enviado."""
    id: str
    status: str  # sent, delivered, read, failed
    timestamp: str
    recipient_id: str


class WhatsAppMetadata(BaseModel):
    display_phone_number: str
    phone_number_id: str


class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: WhatsAppMetadata
    contacts: Optional[list[WhatsAppContact]] = None
    messages: Optional[list[WhatsAppMessage]] = None
    statuses: Optional[list[WhatsAppStatus]] = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    """Payload raíz del webhook de WhatsApp."""
    object: str
    entry: list[WhatsAppEntry]

    def get_messages(self) -> list[WhatsAppMessage]:
        """Extrae todos los mensajes del payload."""
        messages = []
        for entry in self.entry:
            for change in entry.changes:
                if change.value.messages:
                    messages.extend(change.value.messages)
        return messages

    def get_contact_name(self) -> Optional[str]:
        """Extrae el nombre del contacto del primer entry."""
        for entry in self.entry:
            for change in entry.changes:
                if change.value.contacts:
                    return change.value.contacts[0].profile.name
        return None

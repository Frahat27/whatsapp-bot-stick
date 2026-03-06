"""
Importar todos los modelos para registrarlos con SQLAlchemy.
Garantiza que las relaciones entre modelos se resuelvan correctamente.
"""

from src.models.base import Base  # noqa: F401
from src.models.conversation import Conversation, ContactType  # noqa: F401
from src.models.message import Message, MessageRole, MessageType  # noqa: F401
from src.models.conversation_state import (  # noqa: F401
    ConversationState,
    ConversationStatus,
    ConversationSummary,
)

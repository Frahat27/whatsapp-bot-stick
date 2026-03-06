"""
Configuración de pytest — fixtures compartidas.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from src.config import get_settings


# =============================================================================
# DB Fixtures (para tests de integración con Neon real + rollback)
# =============================================================================

@pytest_asyncio.fixture
async def db_session():
    """
    Provee una sesión async de DB que NO persiste datos.

    Técnica: connection-level transaction + monkey-patch commit → flush.
    - Se inicia una transacción real a nivel de connection
    - session.commit() del código bajo test se reemplaza por session.flush()
      (los datos se escriben al DB para queries pero la tx nunca commitea)
    - Al final del test, se hace rollback a nivel de connection → nada persiste
    """
    settings = get_settings()
    if not settings.database_url:
        pytest.skip("DATABASE_URL no configurada")

    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.connect() as connection:
        # Iniciar transacción real a nivel de connection
        transaction = await connection.begin()

        # Crear session vinculada a esta connection
        session = AsyncSession(bind=connection, expire_on_commit=False)

        # Monkey-patch: commit() → flush() para que el código bajo test
        # no cierre la transacción real
        _original_commit = session.commit

        async def _fake_commit():
            await session.flush()

        session.commit = _fake_commit

        yield session

        # Cleanup: cerrar session y rollback transacción real
        await session.close()
        await transaction.rollback()

    await engine.dispose()


# =============================================================================
# WhatsApp Webhook Payloads
# =============================================================================

@pytest.fixture
def sample_webhook_payload():
    """Payload real de un webhook de WhatsApp (mensaje de texto)."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "5491100001111",
                                "phone_number_id": "111111111",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Franco Hatzerian"},
                                    "wa_id": "5491123266671",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "5491123266671",
                                    "id": "wamid.HBgNNTQ5MTEyMzI2NjY3MRUCABEYEjBFNjZBMjE2",
                                    "timestamp": "1709550000",
                                    "type": "text",
                                    "text": {"body": "Hola, quiero sacar un turno"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_status_payload():
    """Payload de status update (delivered/read)."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "5491100001111",
                                "phone_number_id": "111111111",
                            },
                            "statuses": [
                                {
                                    "id": "wamid.xxx",
                                    "status": "delivered",
                                    "timestamp": "1709550100",
                                    "recipient_id": "5491123266671",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

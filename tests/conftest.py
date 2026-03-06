"""
Configuración de pytest.
"""

import pytest


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

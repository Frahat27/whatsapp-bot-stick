"""
Tests para el endpoint /health.

NOTA: Estos tests requieren que las dependencias estén instaladas.
Para Fase 0, testeamos los schemas y el webhook parsing (sin DB).
"""

from src.schemas.webhook import WhatsAppWebhookPayload


class TestWebhookParsing:
    """Tests de parsing del payload de WhatsApp."""

    def test_parse_text_message(self, sample_webhook_payload):
        """Parsear un mensaje de texto standard."""
        payload = WhatsAppWebhookPayload.model_validate(sample_webhook_payload)
        assert payload.object == "whatsapp_business_account"
        assert len(payload.entry) == 1

        messages = payload.get_messages()
        assert len(messages) == 1
        assert messages[0].type == "text"
        assert messages[0].text.body == "Hola, quiero sacar un turno"
        assert messages[0].from_ == "5491123266671"

    def test_get_contact_name(self, sample_webhook_payload):
        """Extraer nombre del contacto."""
        payload = WhatsAppWebhookPayload.model_validate(sample_webhook_payload)
        assert payload.get_contact_name() == "Franco Hatzerian"

    def test_parse_status_update(self, sample_status_payload):
        """Status updates no tienen mensajes."""
        payload = WhatsAppWebhookPayload.model_validate(sample_status_payload)
        messages = payload.get_messages()
        assert len(messages) == 0

    def test_get_contact_name_no_contacts(self, sample_status_payload):
        """Status updates no tienen contacts."""
        payload = WhatsAppWebhookPayload.model_validate(sample_status_payload)
        assert payload.get_contact_name() is None

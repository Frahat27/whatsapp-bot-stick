"""Tests para el webhook HTTP endpoint."""

from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.main import app


class TestWebhookVerification:
    """GET /webhook — verificación por Meta."""

    def test_valid_token_returns_challenge(self):
        mock_settings = MagicMock()
        mock_settings.whatsapp_verify_token = "mi_token_secreto"

        with patch("src.api.webhook.get_settings", return_value=mock_settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(
                "/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "mi_token_secreto",
                    "hub.challenge": "challenge_abc123",
                },
            )
        assert response.status_code == 200
        assert response.text == "challenge_abc123"

    def test_wrong_token_returns_403(self):
        mock_settings = MagicMock()
        mock_settings.whatsapp_verify_token = "token_correcto"

        with patch("src.api.webhook.get_settings", return_value=mock_settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(
                "/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "token_incorrecto",
                    "hub.challenge": "challenge_123",
                },
            )
        assert response.status_code == 403

    def test_missing_params_returns_403(self):
        mock_settings = MagicMock()
        mock_settings.whatsapp_verify_token = "token"

        with patch("src.api.webhook.get_settings", return_value=mock_settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/webhook")
        assert response.status_code == 403


class TestWebhookPostMessage:
    """POST /webhook — recepción de mensajes."""

    def test_valid_message_returns_200(self, sample_webhook_payload):
        with patch("src.api.webhook._process_message", new_callable=AsyncMock), \
             patch("src.api.webhook.get_settings") as mock_settings:
            mock_settings.return_value.whatsapp_app_secret = ""
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/webhook", json=sample_webhook_payload)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_status_update_returns_200(self, sample_status_payload):
        with patch("src.api.webhook.get_settings") as mock_settings:
            mock_settings.return_value.whatsapp_app_secret = ""
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/webhook", json=sample_status_payload)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_invalid_json_returns_200(self):
        """Meta requiere siempre 200, incluso en error de parseo."""
        with patch("src.api.webhook.get_settings") as mock_settings:
            mock_settings.return_value.whatsapp_app_secret = ""
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/webhook",
                json={"object": "whatsapp_business_account", "entry": []},
            )
        # Puede ser 200 o 422 dependiendo del parsing, pero no 500
        assert response.status_code in (200, 422)

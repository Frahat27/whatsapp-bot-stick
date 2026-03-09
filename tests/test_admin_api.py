"""
Tests para Admin API endpoints (auth + admin).

Testea login JWT, endpoints protegidos, simulate, y state update.
Usa mocks para evitar dependencias de DB real.
"""
from __future__ import annotations

from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app


# =========================================================================
# Helpers
# =========================================================================

def _mock_settings():
    """Crea un mock de settings con JWT config y admin passwords."""
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    s = MagicMock()
    s.jwt_secret_key = "test-secret-key-for-testing"
    s.jwt_algorithm = "HS256"
    s.jwt_access_token_expire_hours = 24
    s.admin_phone_list = ["1123266671", "1159531564"]
    s.admin_name_list = ["Franco", "Cynthia"]
    s.admin_password_hash_franco = pwd_context.hash("testpass123")
    s.admin_password_hash_cynthia = pwd_context.hash("testpass456")
    s.whatsapp_verify_token = ""
    s.whatsapp_app_secret = ""
    return s


def _get_token(client: TestClient, username: str = "franco", password: str = "testpass123") -> str:
    """Helper: login y retorna el access_token."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


# =========================================================================
# Auth Tests
# =========================================================================

class TestAuthLogin:
    """POST /api/v1/auth/login"""

    def test_valid_login_returns_token(self):
        settings = _mock_settings()
        with patch("src.api.auth.get_settings", return_value=settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "franco", "password": "testpass123"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["admin_name"] == "Franco"

    def test_wrong_password_returns_401(self):
        settings = _mock_settings()
        with patch("src.api.auth.get_settings", return_value=settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "franco", "password": "wrongpass"},
            )
        assert response.status_code == 401

    def test_unknown_user_returns_401(self):
        settings = _mock_settings()
        with patch("src.api.auth.get_settings", return_value=settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "hacker", "password": "testpass123"},
            )
        assert response.status_code == 401

    def test_case_insensitive_username(self):
        settings = _mock_settings()
        with patch("src.api.auth.get_settings", return_value=settings):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "FRANCO", "password": "testpass123"},
            )
        assert response.status_code == 200


class TestProtectedEndpoints:
    """Endpoints que requieren JWT."""

    def test_no_token_returns_401(self):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/admin/conversations")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(
            "/api/v1/admin/conversations",
            headers={"Authorization": "Bearer invalid-token-xyz"},
        )
        assert response.status_code == 401

    def test_valid_token_passes_auth(self):
        settings = _mock_settings()
        with patch("src.api.auth.get_settings", return_value=settings), \
             patch("src.api.admin.get_db") as mock_get_db:
            # Mock DB para que el endpoint no falle por DB
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value = mock_session

            client = TestClient(app, raise_server_exceptions=False)
            token = _get_token(client)
            response = client.get(
                "/api/v1/admin/conversations",
                headers={"Authorization": f"Bearer {token}"},
            )
        # Puede ser 200 o 500 (por DB mock), pero NO 401
        assert response.status_code != 401


# =========================================================================
# Simulate Endpoint Tests
# =========================================================================

class TestSimulateEndpoint:
    """POST /api/v1/admin/simulate"""

    def test_simulate_requires_auth(self):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/admin/simulate",
            json={"phone": "1155551234", "content": "Hola"},
        )
        assert response.status_code == 401

    def test_simulate_requires_phone_and_content(self):
        settings = _mock_settings()
        with patch("src.api.auth.get_settings", return_value=settings):
            client = TestClient(app, raise_server_exceptions=False)
            token = _get_token(client)
            # Missing content
            response = client.post(
                "/api/v1/admin/simulate",
                json={"phone": "1155551234"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422


# =========================================================================
# State Update Tests
# =========================================================================

class TestStateUpdate:
    """PATCH /api/v1/admin/conversations/{id}/state"""

    def test_state_update_requires_auth(self):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.patch(
            "/api/v1/admin/conversations/1/state",
            json={"status": "admin_takeover"},
        )
        assert response.status_code == 401

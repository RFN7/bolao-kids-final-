import pytest
from fastapi.testclient import TestClient

_REGISTER_URL = "/auth/register"
_LOGIN_URL = "/auth/login"
_REFRESH_URL = "/auth/refresh"
_LOGOUT_URL = "/auth/logout"

_USER = {"name": "João Silva", "email": "joao@test.com", "password": "senha123"}


def _register(client: TestClient, payload: dict | None = None) -> dict:
    resp = client.post(_REGISTER_URL, json=payload or _USER)
    return resp


def _login(client: TestClient, identifier: str = "joao@test.com", password: str = "senha123") -> dict:
    return client.post(_LOGIN_URL, json={"identifier": identifier, "password": password})


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------

def test_register_success(client):
    resp = _register(client)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "João Silva"
    assert data["email"] == "joao@test.com"
    assert "id" in data
    assert "created_at" in data
    assert "password_hash" not in data


def test_register_without_email_and_phone(client):
    resp = _register(client, {"name": "João", "password": "senha123"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_duplicate_email(client):
    _register(client)
    resp = _register(client)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_success(client):
    _register(client)
    resp = _login(client)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["expires_in"] == 15 * 60
    assert data["user"]["name"] == "João Silva"


def test_login_wrong_password(client):
    _register(client)
    resp = _login(client, password="errada123")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_identifier(client):
    resp = _login(client, identifier="naoexiste@test.com")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

def test_refresh_token_valid(client):
    _register(client)
    tokens = _login(client).json()
    resp = client.post(_REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["expires_in"] == 15 * 60


def test_refresh_token_invalid(client):
    resp = client.post(_REFRESH_URL, json={"refresh_token": "token.invalido.aqui"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_TOKEN"


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def test_logout(client):
    _register(client)
    tokens = _login(client).json()

    resp = client.post(
        _LOGOUT_URL,
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 204

    # Após logout, refresh_token deve estar revogado
    resp2 = client.post(_REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})
    assert resp2.status_code == 401
    assert resp2.json()["error"]["code"] == "TOKEN_REVOKED"

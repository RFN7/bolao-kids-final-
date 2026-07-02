import pytest
from fastapi.testclient import TestClient

_USER = {"name": "João Silva", "email": "joao@test.com", "password": "senha123"}
_USER2 = {"name": "Maria Oliveira", "email": "maria@test.com", "password": "senha456"}
_CHILD = {"name": "Pedro"}
_FAMILY = {"child": _CHILD}


def _login(client: TestClient, user: dict) -> dict:
    client.post("/auth/register", json=user)
    resp = client.post("/auth/login", json={"identifier": user["email"], "password": user["password"]})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def user_with_consent(client):
    headers = _login(client, _USER)
    client.post("/auth/consent", json={"consent_version": "1.0"}, headers=headers)
    return headers


@pytest.fixture
def user2_with_consent(client):
    headers = _login(client, _USER2)
    client.post("/auth/consent", json={"consent_version": "1.0"}, headers=headers)
    return headers


# ---------------------------------------------------------------------------
# Consentimento
# ---------------------------------------------------------------------------

def test_create_family_without_consent(client):
    headers = _login(client, _USER)
    resp = client.post("/families", json=_FAMILY, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CONSENT_REQUIRED"


def test_give_consent(client):
    headers = _login(client, _USER)
    resp = client.post("/auth/consent", json={"consent_version": "1.0"}, headers=headers)
    assert resp.status_code == 200
    assert "consented_at" in resp.json()
    assert resp.json()["consent_version"] == "1.0"


# ---------------------------------------------------------------------------
# Criar família
# ---------------------------------------------------------------------------

def test_create_family_success(client, user_with_consent):
    resp = client.post("/families", json=_FAMILY, headers=user_with_consent)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["status"] == "active"
    assert data["child"]["name"] == "Pedro"
    # display_name gerado automaticamente: "Família Silva"
    assert "Silva" in data["display_name"]


def test_create_family_with_display_name(client, user_with_consent):
    payload = {"child": {"name": "Ana"}, "display_name": "Os Campeões"}
    resp = client.post("/families", json=payload, headers=user_with_consent)
    assert resp.status_code == 201
    assert resp.json()["display_name"] == "Os Campeões"


def test_create_family_duplicate_child(client, user_with_consent):
    client.post("/families", json=_FAMILY, headers=user_with_consent)
    resp = client.post("/families", json=_FAMILY, headers=user_with_consent)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "FAMILY_ALREADY_EXISTS_FOR_CHILD"


# ---------------------------------------------------------------------------
# Listar famílias
# ---------------------------------------------------------------------------

def test_list_families(client, user_with_consent):
    client.post("/families", json=_FAMILY, headers=user_with_consent)
    client.post("/families", json={"child": {"name": "Ana"}}, headers=user_with_consent)
    resp = client.get("/families/me", headers=user_with_consent)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_families_filter_by_status(client, user_with_consent):
    resp = client.post("/families", json=_FAMILY, headers=user_with_consent)
    family_id = resp.json()["id"]
    client.patch(f"/families/{family_id}", json={"status": "inactive"}, headers=user_with_consent)
    client.post("/families", json={"child": {"name": "Ana"}}, headers=user_with_consent)

    active = client.get("/families/me?status=active", headers=user_with_consent).json()
    inactive = client.get("/families/me?status=inactive", headers=user_with_consent).json()
    assert len(active) == 1
    assert len(inactive) == 1


# ---------------------------------------------------------------------------
# Editar família
# ---------------------------------------------------------------------------

def test_update_display_name(client, user_with_consent):
    resp = client.post("/families", json=_FAMILY, headers=user_with_consent)
    family_id = resp.json()["id"]
    resp = client.patch(f"/families/{family_id}", json={"display_name": "Família Atualizada"}, headers=user_with_consent)
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Família Atualizada"


def test_update_display_name_empty_string(client, user_with_consent):
    resp = client.post("/families", json=_FAMILY, headers=user_with_consent)
    family_id = resp.json()["id"]
    resp = client.patch(f"/families/{family_id}", json={"display_name": ""}, headers=user_with_consent)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_family_forbidden(client, user_with_consent, user2_with_consent):
    resp = client.post("/families", json=_FAMILY, headers=user_with_consent)
    family_id = resp.json()["id"]
    resp = client.patch(f"/families/{family_id}", json={"display_name": "Hack"}, headers=user2_with_consent)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"

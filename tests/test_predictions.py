import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

_USER = {"name": "João Silva", "email": "joao@test.com", "password": "senha123"}
_USER2 = {"name": "Maria Santos", "email": "maria@test.com", "password": "senha456"}

_PRED_PAI = {"author_type": "pai", "home_score_pred": 2, "away_score_pred": 1}
_PRED_FILHO = {"author_type": "filho", "home_score_pred": 1, "away_score_pred": 1}
_PRED_FAMILIA = {"author_type": "familia", "home_score_pred": 3, "away_score_pred": 0}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup(client, db_session):
    client.post("/auth/register", json=_USER)
    login = client.post("/auth/login", json={"identifier": _USER["email"], "password": _USER["password"]})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/auth/consent", json={"consent_version": "1.0"}, headers=headers)

    family_resp = client.post("/families", json={"child": {"name": "Pedro"}}, headers=headers)
    assert family_resp.status_code == 201, family_resp.text
    family_id = family_resp.json()["id"]

    games = client.get("/games").json()
    assert len(games) >= 1
    game_id = games[0]["id"]

    return {"headers": headers, "family_id": family_id, "game_id": game_id}


def _make_payload(setup, author_type: str, home: int = 2, away: int = 1) -> dict:
    return {
        "family_id": setup["family_id"],
        "game_id": setup["game_id"],
        "author_type": author_type,
        "home_score_pred": home,
        "away_score_pred": away,
    }


# ---------------------------------------------------------------------------
# Criação de palpites
# ---------------------------------------------------------------------------

def test_create_prediction_pai(setup, client):
    resp = client.post("/predictions", json=_make_payload(setup, "pai"), headers=setup["headers"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["author_type"] == "pai"
    assert data["home_score_pred"] == 2
    assert data["away_score_pred"] == 1
    assert data["locked"] is False
    assert data["points_earned"] is None


def test_create_prediction_filho(setup, client):
    resp = client.post("/predictions", json=_make_payload(setup, "filho", 1, 1), headers=setup["headers"])
    assert resp.status_code == 201
    assert resp.json()["author_type"] == "filho"


def test_create_prediction_familia(setup, client):
    resp = client.post("/predictions", json=_make_payload(setup, "familia", 3, 0), headers=setup["headers"])
    assert resp.status_code == 201
    assert resp.json()["author_type"] == "familia"


# ---------------------------------------------------------------------------
# RN-17: is_complete
# ---------------------------------------------------------------------------

def test_is_complete_true_when_all_three_exist(setup, client):
    for author_type in ("pai", "filho", "familia"):
        client.post("/predictions", json=_make_payload(setup, author_type), headers=setup["headers"])

    resp = client.get(
        f"/games/{setup['game_id']}/predictions/me",
        params={"family_id": setup["family_id"]},
        headers=setup["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_complete"] is True
    assert data["pai"] is not None
    assert data["filho"] is not None
    assert data["familia"] is not None


def test_is_complete_false_when_missing_predictions(setup, client):
    client.post("/predictions", json=_make_payload(setup, "pai"), headers=setup["headers"])

    resp = client.get(
        f"/games/{setup['game_id']}/predictions/me",
        params={"family_id": setup["family_id"]},
        headers=setup["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_complete"] is False
    assert data["pai"] is not None
    assert data["filho"] is None
    assert data["familia"] is None


# ---------------------------------------------------------------------------
# Erros de criação
# ---------------------------------------------------------------------------

def test_prediction_already_exists(setup, client):
    client.post("/predictions", json=_make_payload(setup, "pai"), headers=setup["headers"])
    resp = client.post("/predictions", json=_make_payload(setup, "pai"), headers=setup["headers"])
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "PREDICTION_ALREADY_EXISTS"


def test_create_prediction_game_locked(setup, client, db_session):
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.execute(
        text("UPDATE games SET locks_at = :t WHERE id = :id"),
        {"t": past, "id": uuid.UUID(setup["game_id"])},
    )
    db_session.commit()

    resp = client.post("/predictions", json=_make_payload(setup, "pai"), headers=setup["headers"])
    assert resp.status_code == 423
    assert resp.json()["error"]["code"] == "GAME_LOCKED"


def test_create_prediction_forbidden(setup, client):
    client.post("/auth/register", json=_USER2)
    login2 = client.post("/auth/login", json={"identifier": _USER2["email"], "password": _USER2["password"]})
    headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    resp = client.post("/predictions", json=_make_payload(setup, "pai"), headers=headers2)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# Atualização
# ---------------------------------------------------------------------------

def test_update_prediction_success(setup, client):
    create_resp = client.post("/predictions", json=_make_payload(setup, "pai", 2, 1), headers=setup["headers"])
    pred_id = create_resp.json()["id"]

    resp = client.patch(
        f"/predictions/{pred_id}",
        json={"home_score_pred": 3, "away_score_pred": 2},
        headers=setup["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["home_score_pred"] == 3
    assert data["away_score_pred"] == 2


def test_update_prediction_game_locked(setup, client, db_session):
    create_resp = client.post("/predictions", json=_make_payload(setup, "pai"), headers=setup["headers"])
    pred_id = create_resp.json()["id"]

    db_session.execute(
        text("UPDATE predictions SET locked = TRUE WHERE id = :id"),
        {"id": uuid.UUID(pred_id)},
    )
    db_session.commit()

    resp = client.patch(
        f"/predictions/{pred_id}",
        json={"home_score_pred": 3, "away_score_pred": 2},
        headers=setup["headers"],
    )
    assert resp.status_code == 423
    assert resp.json()["error"]["code"] == "GAME_LOCKED"

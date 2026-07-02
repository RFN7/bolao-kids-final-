import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

_USER1 = {"name": "João Silva", "email": "joao@test.com", "password": "senha123"}
_USER2 = {"name": "Maria Santos", "email": "maria@test.com", "password": "senha456"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_ranking_cache():
    from app.cache import redis_client
    for key in redis_client.scan_iter("ranking:*"):
        redis_client.delete(key)
    yield
    for key in redis_client.scan_iter("ranking:*"):
        redis_client.delete(key)


def _register_and_login(client, user_data: dict) -> dict:
    client.post("/auth/register", json=user_data)
    login = client.post("/auth/login", json={"identifier": user_data["email"], "password": user_data["password"]})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/auth/consent", json={"consent_version": "1.0"}, headers=headers)
    return headers


def _create_family(client, headers: dict, child_name: str) -> str:
    resp = client.post("/families", json={"child": {"name": child_name}}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.fixture
def two_families(client, db_session):
    headers1 = _register_and_login(client, _USER1)
    family1_id = _create_family(client, headers1, "Pedro")

    headers2 = _register_and_login(client, _USER2)
    family2_id = _create_family(client, headers2, "Ana")

    return {
        "headers1": headers1, "family1_id": family1_id,
        "headers2": headers2, "family2_id": family2_id,
    }


@pytest.fixture
def setup(client, db_session):
    headers = _register_and_login(client, _USER1)
    family_id = _create_family(client, headers, "Pedro")
    games = client.get("/games").json()
    game_id = games[0]["id"]
    return {"headers": headers, "family_id": family_id, "game_id": game_id}


# ---------------------------------------------------------------------------
# GET /ranking ordenação por pontuação
# ---------------------------------------------------------------------------

def test_ranking_ordered_by_points_desc(two_families, client, db_session):
    f1 = two_families["family1_id"]
    f2 = two_families["family2_id"]

    # family1 → 10 pts, family2 → 5 pts
    db_session.execute(
        text("UPDATE family_statistics SET total_points_family=10 WHERE family_id=:id"),
        {"id": uuid.UUID(f1)},
    )
    db_session.execute(
        text("UPDATE family_statistics SET total_points_family=5 WHERE family_id=:id"),
        {"id": uuid.UUID(f2)},
    )
    db_session.commit()

    resp = client.get("/ranking", headers=two_families["headers1"])
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] == 2
    assert len(data["ranking"]) == 2
    assert data["ranking"][0]["position"] == 1
    assert data["ranking"][0]["total_points_family"] == 10
    assert data["ranking"][1]["position"] == 2
    assert data["ranking"][1]["total_points_family"] == 5


# ---------------------------------------------------------------------------
# RN-25: desempate por exact_hits
# ---------------------------------------------------------------------------

def test_tiebreak_by_exact_hits(two_families, client, db_session):
    f1 = two_families["family1_id"]
    f2 = two_families["family2_id"]

    # Ambas com 5 pts; family2 tem 1 exact_hit → aparece primeiro
    db_session.execute(
        text("UPDATE family_statistics SET total_points_family=5, exact_hits=0 WHERE family_id=:id"),
        {"id": uuid.UUID(f1)},
    )
    db_session.execute(
        text("UPDATE family_statistics SET total_points_family=5, exact_hits=1 WHERE family_id=:id"),
        {"id": uuid.UUID(f2)},
    )
    db_session.commit()

    resp = client.get("/ranking", headers=two_families["headers1"])
    assert resp.status_code == 200
    ranking = resp.json()["ranking"]

    assert ranking[0]["position"] == 1
    assert str(ranking[0]["family"]["id"]) == f2  # mais exact_hits
    assert ranking[1]["position"] == 2
    assert str(ranking[1]["family"]["id"]) == f1


# ---------------------------------------------------------------------------
# RN-26: família inativa não aparece
# ---------------------------------------------------------------------------

def test_inactive_family_excluded_from_ranking(two_families, client, db_session):
    f1 = two_families["family1_id"]
    f2 = two_families["family2_id"]

    db_session.execute(
        text("UPDATE family_statistics SET total_points_family=10 WHERE family_id=:id"),
        {"id": uuid.UUID(f1)},
    )
    db_session.execute(
        text("UPDATE family_statistics SET total_points_family=20 WHERE family_id=:id"),
        {"id": uuid.UUID(f2)},
    )
    # Desativa family2
    db_session.execute(
        text("UPDATE families SET status='inactive' WHERE id=:id"),
        {"id": uuid.UUID(f2)},
    )
    db_session.commit()

    resp = client.get("/ranking", headers=two_families["headers1"])
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] == 1
    assert len(data["ranking"]) == 1
    assert str(data["ranking"][0]["family"]["id"]) == f1


# ---------------------------------------------------------------------------
# GET /ranking/history após apply_results
# ---------------------------------------------------------------------------

def test_ranking_history_after_apply_results(setup, client, db_session):
    from app.modules.scoring.service import apply_results

    headers = setup["headers"]
    family_id = setup["family_id"]
    game_id = setup["game_id"]

    for author_type in ("pai", "filho", "familia"):
        r = client.post("/predictions", json={
            "family_id": family_id, "game_id": game_id,
            "author_type": author_type,
            "home_score_pred": 2, "away_score_pred": 1,
        }, headers=headers)
        assert r.status_code == 201, r.text

    db_session.execute(
        text("UPDATE games SET status='finished', home_score=2, away_score=1 WHERE id=:id"),
        {"id": uuid.UUID(game_id)},
    )
    db_session.commit()

    apply_results(uuid.UUID(game_id))

    resp = client.get("/ranking/history", params={"family_id": family_id}, headers=headers)
    assert resp.status_code == 200
    history = resp.json()["history"]
    assert len(history) == 1
    assert history[0]["position"] == 1
    assert history[0]["total_points_family"] == 10
    assert isinstance(history[0]["round"], str) and len(history[0]["round"]) > 0


# ---------------------------------------------------------------------------
# FORBIDDEN ao acessar histórico de outra família
# ---------------------------------------------------------------------------

def test_ranking_history_forbidden_other_user(two_families, client):
    # headers1 tenta ver histórico da family2
    resp = client.get(
        "/ranking/history",
        params={"family_id": two_families["family2_id"]},
        headers=two_families["headers1"],
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# FAMILY_NOT_FOUND para família inexistente
# ---------------------------------------------------------------------------

def test_ranking_history_family_not_found(setup, client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(
        "/ranking/history",
        params={"family_id": fake_id},
        headers=setup["headers"],
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "FAMILY_NOT_FOUND"


# ---------------------------------------------------------------------------
# Cache Redis: segunda chamada servida do cache
# ---------------------------------------------------------------------------

def test_ranking_redis_cache(setup, client, db_session):
    headers = setup["headers"]
    family_id = setup["family_id"]

    # Primeira chamada: DB → cache (0 pts)
    resp1 = client.get("/ranking", headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()

    # Modifica DB diretamente para 9999 pts
    db_session.execute(
        text("UPDATE family_statistics SET total_points_family=9999 WHERE family_id=:id"),
        {"id": uuid.UUID(family_id)},
    )
    db_session.commit()

    # Segunda chamada: deve retornar dados do cache (não os 9999)
    resp2 = client.get("/ranking", headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data1 == data2
    for entry in data2["ranking"]:
        assert entry["total_points_family"] != 9999

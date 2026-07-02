import uuid

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_game_ids(client) -> list[str]:
    return [g["id"] for g in client.get("/games").json()]


# ---------------------------------------------------------------------------
# Geração
# ---------------------------------------------------------------------------

def test_generation_creates_exactly_two(client):
    from app.modules.curiosities.generator import generate_for_game

    game_id = uuid.UUID(_get_game_ids(client)[0])
    generate_for_game(game_id)  # idempotent — lifespan já gerou

    resp = client.get(f"/games/{game_id}/curiosities")
    assert resp.status_code == 200
    assert len(resp.json()["curiosities"]) == 2


def test_generation_is_idempotent(client):
    from app.modules.curiosities.generator import generate_for_game

    game_id = uuid.UUID(_get_game_ids(client)[0])

    generate_for_game(game_id)
    generate_for_game(game_id)
    generate_for_game(game_id)

    resp = client.get(f"/games/{game_id}/curiosities")
    assert resp.status_code == 200
    assert len(resp.json()["curiosities"]) == 2


def test_text_max_160_chars(client):
    for game_id in _get_game_ids(client):
        resp = client.get(f"/games/{game_id}/curiosities")
        assert resp.status_code == 200
        for c in resp.json()["curiosities"]:
            assert len(c["text"]) <= 160, f"Texto excede 160 chars: {c['text']!r}"


def test_stat_source_is_fallback_for_mock_teams(client):
    for game_id in _get_game_ids(client):
        resp = client.get(f"/games/{game_id}/curiosities")
        assert resp.status_code == 200
        for c in resp.json()["curiosities"]:
            assert c["stat_source"] == "fallback"


# ---------------------------------------------------------------------------
# GET /games/{id}/curiosities
# ---------------------------------------------------------------------------

def test_get_curiosities_returns_both_roles(client):
    game_id = _get_game_ids(client)[0]
    resp = client.get(f"/games/{game_id}/curiosities")
    assert resp.status_code == 200

    data = resp.json()
    assert "curiosities" in data
    assert len(data["curiosities"]) == 2

    roles = {c["role"] for c in data["curiosities"]}
    assert roles == {"mandante", "visitante"}

    for c in data["curiosities"]:
        assert "team" in c
        assert "text" in c
        assert "stat_source" in c
        assert c["team"]["name"] in {
            "Flamengo", "Palmeiras", "Corinthians", "São Paulo"
        }


def test_get_curiosities_game_not_found(client):
    resp = client.get("/games/00000000-0000-0000-0000-000000000000/curiosities")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "GAME_NOT_FOUND"

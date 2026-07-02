import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def test_sync_games_populates_db(client):
    from app.modules.football.service import sync_games

    # lifespan already called sync once; call again to confirm idempotency
    sync_games()

    resp = client.get("/games")
    assert resp.status_code == 200
    games = resp.json()
    assert len(games) == 2

    team_names = {g["home_team"]["name"] for g in games} | {g["away_team"]["name"] for g in games}
    assert "Flamengo" in team_names
    assert "Palmeiras" in team_names
    assert "Corinthians" in team_names
    assert "São Paulo" in team_names


# ---------------------------------------------------------------------------
# GET /games
# ---------------------------------------------------------------------------

def test_get_games_returns_all(client):
    resp = client.get("/games")
    assert resp.status_code == 200
    games = resp.json()
    assert len(games) == 2
    for g in games:
        assert "id" in g
        assert "home_team" in g
        assert "away_team" in g
        assert "kickoff_at" in g
        assert "locks_at" in g
        assert "status" in g


def test_get_games_filter_scheduled(client):
    resp = client.get("/games?status=scheduled")
    assert resp.status_code == 200
    games = resp.json()
    assert len(games) == 2
    for g in games:
        assert g["status"] == "scheduled"


def test_get_games_filter_unknown_status_returns_empty(client):
    resp = client.get("/games?status=finished")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_games_filter_by_round_id(client):
    games = client.get("/games").json()
    round_id = games[0]["round_id"]
    resp = client.get(f"/games?round_id={round_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2  # both games are in the same round


# ---------------------------------------------------------------------------
# GET /games/{game_id}
# ---------------------------------------------------------------------------

def test_get_game_by_id(client):
    games = client.get("/games").json()
    game_id = games[0]["id"]

    resp = client.get(f"/games/{game_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == game_id
    assert "home_team" in data
    assert "away_team" in data


def test_get_game_not_found(client):
    resp = client.get("/games/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "GAME_NOT_FOUND"

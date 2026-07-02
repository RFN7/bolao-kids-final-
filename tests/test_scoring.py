import uuid

import pytest
from sqlalchemy import text

from app.modules.scoring.service import calculate_points

_USER = {"name": "João Silva", "email": "joao@test.com", "password": "senha123"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def scoring_setup(client, db_session):
    client.post("/auth/register", json=_USER)
    login = client.post("/auth/login", json={"identifier": _USER["email"], "password": _USER["password"]})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/auth/consent", json={"consent_version": "1.0"}, headers=headers)

    family_resp = client.post("/families", json={"child": {"name": "Pedro"}}, headers=headers)
    assert family_resp.status_code == 201, family_resp.text
    family_id = family_resp.json()["id"]

    games = client.get("/games").json()
    game_id = games[0]["id"]

    return {"headers": headers, "family_id": family_id, "game_id": game_id}


# ---------------------------------------------------------------------------
# Testes unitários de calculate_points
# ---------------------------------------------------------------------------

def test_exact_score_returns_10_points():
    assert calculate_points(2, 1, 2, 1) == 10


def test_correct_result_wrong_score_returns_5_points():
    assert calculate_points(1, 0, 3, 1) == 5  # home wins both


def test_draw_predicted_and_real_returns_5_points():
    assert calculate_points(1, 1, 0, 0) == 5  # draw both


def test_wrong_result_returns_0_points():
    assert calculate_points(2, 1, 0, 1) == 0  # home win vs away win


# ---------------------------------------------------------------------------
# Testes de integração de apply_results
# ---------------------------------------------------------------------------

def test_apply_results_updates_points_earned_on_all_three_predictions(scoring_setup, client, db_session):
    from app.modules.predictions.models import Prediction
    from app.modules.scoring.service import apply_results

    headers = scoring_setup["headers"]
    family_id = scoring_setup["family_id"]
    game_id = scoring_setup["game_id"]

    for author_type in ("pai", "filho", "familia"):
        r = client.post("/predictions", json={
            "family_id": family_id, "game_id": game_id,
            "author_type": author_type, "home_score_pred": 2, "away_score_pred": 1,
        }, headers=headers)
        assert r.status_code == 201, r.text

    db_session.execute(
        text("UPDATE games SET status='finished', home_score=2, away_score=1 WHERE id=:id"),
        {"id": uuid.UUID(game_id)},
    )
    db_session.commit()

    apply_results(uuid.UUID(game_id))

    preds = db_session.query(Prediction).filter(Prediction.game_id == uuid.UUID(game_id)).all()
    assert len(preds) == 3
    for pred in preds:
        db_session.refresh(pred)
        assert pred.points_earned == 10


def test_apply_results_updates_family_statistics_correctly(scoring_setup, client, db_session):
    from app.modules.families.models import FamilyStatistics
    from app.modules.scoring.service import apply_results

    headers = scoring_setup["headers"]
    family_id = scoring_setup["family_id"]
    game_id = scoring_setup["game_id"]

    for author_type, home, away in [("pai", 1, 0), ("filho", 1, 0), ("familia", 2, 1)]:
        client.post("/predictions", json={
            "family_id": family_id, "game_id": game_id,
            "author_type": author_type, "home_score_pred": home, "away_score_pred": away,
        }, headers=headers)

    # Real: 2-1 → familia(2-1)=exact(10), pai(1-0)=correct result(5), filho(1-0)=correct result(5)
    db_session.execute(
        text("UPDATE games SET status='finished', home_score=2, away_score=1 WHERE id=:id"),
        {"id": uuid.UUID(game_id)},
    )
    db_session.commit()

    apply_results(uuid.UUID(game_id))

    stats = (
        db_session.query(FamilyStatistics)
        .filter(FamilyStatistics.family_id == uuid.UUID(family_id))
        .first()
    )
    db_session.refresh(stats)
    assert stats.games_played == 1
    assert stats.total_points_family == 10  # familia: exact
    assert stats.total_points_pai == 5       # pai: correct result
    assert stats.total_points_filho == 5     # filho: correct result
    assert stats.exact_hits == 1             # familia acertou placar exato
    assert stats.result_hits == 0            # familia não foi result_hit (foi exact)

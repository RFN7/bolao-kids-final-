import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.modules.football import external_client
from app.modules.football.models import Competition, Game, Round, Team
from app.shared.exceptions import AppException


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def sync_games() -> None:
    from app.database import SessionLocal

    db: Session = SessionLocal()
    try:
        data = external_client.fetch_games()
        now = datetime.now(timezone.utc)

        # --- teams ---
        team_map: dict[str, Team] = {}
        for t in data["teams"]:
            team = db.query(Team).filter(Team.external_api_id == t["external_api_id"]).first()
            if team is None:
                team = Team(**t)
                db.add(team)
            else:
                team.name = t["name"]
                team.short_name = t["short_name"]
                team.crest_url = t["crest_url"]
                team.country = t["country"]
                team.updated_at = now
            db.flush()
            team_map[t["external_api_id"]] = team

        # --- competition ---
        c = data["competition"]
        comp = db.query(Competition).filter(Competition.external_api_id == c["external_api_id"]).first()
        if comp is None:
            comp = Competition(**c)
            db.add(comp)
        else:
            comp.name = c["name"]
            comp.season = c["season"]
            comp.type = c["type"]
        db.flush()

        # --- round ---
        r = data["round"]
        round_ = (
            db.query(Round)
            .filter(Round.competition_id == comp.id, Round.name == r["name"])
            .first()
        )
        if round_ is None:
            round_ = Round(competition_id=comp.id, **r)
            db.add(round_)
        else:
            round_.start_date = r["start_date"]
            round_.end_date = r["end_date"]
        db.flush()

        # --- games ---
        for g in data["games"]:
            home_team = team_map[g["home_team_external_id"]]
            away_team = team_map[g["away_team_external_id"]]

            game = db.query(Game).filter(Game.external_api_id == g["external_api_id"]).first()
            if game is None:
                game = Game(
                    external_api_id=g["external_api_id"],
                    round_id=round_.id,
                    competition_id=comp.id,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    kickoff_at=g["kickoff_at"],
                    status=g["status"],
                    home_score=g["home_score"],
                    away_score=g["away_score"],
                    locks_at=g["locks_at"],
                )
                db.add(game)
            else:
                game.kickoff_at = g["kickoff_at"]
                game.status = g["status"]
                game.home_score = g["home_score"]
                game.away_score = g["away_score"]
                game.locks_at = g["locks_at"]
                game.updated_at = now

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def _games_query(db: Session):
    return db.query(Game).options(
        selectinload(Game.home_team),
        selectinload(Game.away_team),
    )


def get_games(round_id: Optional[uuid.UUID], status: Optional[str], db: Session) -> list[Game]:
    q = _games_query(db)
    if round_id:
        q = q.filter(Game.round_id == round_id)
    if status:
        q = q.filter(Game.status == status)
    return q.all()


def get_game(game_id: uuid.UUID, db: Session) -> Game:
    game = _games_query(db).filter(Game.id == game_id).first()
    if not game:
        raise AppException("GAME_NOT_FOUND", "Jogo não encontrado", 404)
    return game

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.modules.football import external_client
from app.modules.football.models import Competition, Game, Round, Team
from app.shared.exceptions import AppException

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def _upsert_team(db: Session, data: dict, now: datetime) -> Team:
    team = db.query(Team).filter(Team.external_api_id == data["external_api_id"]).first()
    if team is None:
        team = Team(
            external_api_id=data["external_api_id"],
            name=data["name"],
            crest_url=data.get("crest_url"),
            country="Brazil",
        )
        db.add(team)
    else:
        team.name = data["name"]
        team.crest_url = data.get("crest_url")
        team.updated_at = now
    db.flush()
    return team


def _upsert_competition(db: Session, data: dict) -> Competition:
    comp = (
        db.query(Competition)
        .filter(Competition.external_api_id == data["external_api_id"])
        .first()
    )
    if comp is None:
        comp = Competition(**data)
        db.add(comp)
    else:
        comp.name = data["name"]
        comp.season = data["season"]
        comp.type = data["type"]
    db.flush()
    return comp


def _upsert_games(db: Session, comp: Competition, games: list[dict], now: datetime) -> int:
    """Upserts teams, round, and games for a batch of parsed fixtures.
    Returns how many games were upserted."""
    count = 0
    for g in games:
        home_team = _upsert_team(db, g["home_team"], now)
        away_team = _upsert_team(db, g["away_team"], now)

        round_name = g.get("round_name") or "Rodada atual"
        round_ = (
            db.query(Round)
            .filter(Round.competition_id == comp.id, Round.name == round_name)
            .first()
        )
        if round_ is None:
            round_ = Round(competition_id=comp.id, name=round_name)
            db.add(round_)
            db.flush()

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
            game.round_id = round_.id
            game.home_team_id = home_team.id
            game.away_team_id = away_team.id
            game.kickoff_at = g["kickoff_at"]
            game.status = g["status"]
            game.home_score = g["home_score"]
            game.away_score = g["away_score"]
            game.locks_at = g["locks_at"]
            game.updated_at = now
        count += 1
    return count


# Temporada 2024 encerrada -> fetch_current_round(current=true) não resolve mais.
# Sincroniza esta rodada como fallback para termos dados de exemplo em produção.
FALLBACK_ROUND = "Regular Season - 1"


def sync_games() -> None:
    from app.database import SessionLocal

    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        competitions = external_client.fetch_competitions()
        logger.info("sync_games: %d competições retornadas pela API", len(competitions))

        for c in competitions:
            comp = _upsert_competition(db, c)
            logger.info(
                "sync_games: processando competição %s (%s)",
                c["external_api_id"],
                c["name"],
            )

            current_round = external_client.fetch_current_round(
                c["external_api_id"], season=2024
            )
            if not current_round:
                logger.warning(
                    "sync_games: nenhuma rodada atual para competição %s (%s); "
                    "usando fallback '%s'",
                    c["external_api_id"],
                    c["name"],
                    FALLBACK_ROUND,
                )
                current_round = FALLBACK_ROUND
            else:
                logger.info(
                    "sync_games: rodada atual para competição %s: %s",
                    c["external_api_id"],
                    current_round,
                )

            games = external_client.fetch_games(
                c["external_api_id"], season=2024, round=current_round
            )
            logger.info(
                "sync_games: %d jogos retornados para competição %s, rodada %s",
                len(games),
                c["external_api_id"],
                current_round,
            )

            count = _upsert_games(db, comp, games, now)
            logger.info(
                "sync_games: %d jogos upsertados para competição %s",
                count,
                c["external_api_id"],
            )

        db.commit()
        logger.info("sync_games: commit realizado com sucesso")
    except Exception:
        db.rollback()
        logger.exception("sync_games: falha durante sincronização, rollback realizado")
        raise
    finally:
        db.close()


def sync_specific_round(league_id: int | str, season: int, round_name: str) -> None:
    """One-off helper to sync a single known round directly, bypassing
    fetch_current_round. Useful to validate the real API-Football
    integration against a round that actually has fixtures, since
    `current=true` only resolves for a season that is presently in progress.
    """
    from app.database import SessionLocal

    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        comp = (
            db.query(Competition)
            .filter(Competition.external_api_id == str(league_id))
            .first()
        )
        if comp is None:
            comp = Competition(
                external_api_id=str(league_id),
                name=f"League {league_id}",
                season=str(season),
                type="league",
            )
            db.add(comp)
            db.flush()

        games = external_client.fetch_games(league_id, season=season, round=round_name)
        count = _upsert_games(db, comp, games, now)

        db.commit()
        logger.info(
            "sync_specific_round: upserted %d games for league=%s season=%s round=%s",
            count,
            league_id,
            season,
            round_name,
        )
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

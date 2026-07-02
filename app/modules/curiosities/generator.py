import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

_FALLBACK_CATALOG: dict[str, str] = {
    "Flamengo": "Um dos clubes mais vitoriosos do Brasil.",
    "Palmeiras": "Maior campeão do Brasileirão com 12 títulos.",
    "Corinthians": "Clube com uma das maiores torcidas do país.",
    "São Paulo": "Tricampeão mundial de clubes.",
}
_DEFAULT_TEXT = "Um dos grandes clubes do futebol brasileiro."

_MAX_TEXT_LEN = 160  # RN-30


def _fetch_from_api(game, team) -> str | None:
    # Placeholder: external curiosities API not integrated yet
    return None


def generate_curiosity(game, team, role: str) -> dict:
    api_text = _fetch_from_api(game, team)

    if api_text is not None:
        text = api_text[:_MAX_TEXT_LEN]
        stat_source = "api"
    else:
        text = _FALLBACK_CATALOG.get(team.name, _DEFAULT_TEXT)
        stat_source = "fallback"

    if len(text) > _MAX_TEXT_LEN:
        raise ValueError(f"Curiosidade excede {_MAX_TEXT_LEN} caracteres (RN-30)")

    return {"text": text, "stat_source": stat_source}


def generate_for_game(game_id: uuid.UUID) -> None:
    from app.database import SessionLocal
    from app.modules.football.models import Game
    from app.modules.curiosities.models import GameCuriosity

    db: Session = SessionLocal()
    try:
        game = (
            db.query(Game)
            .options(selectinload(Game.home_team), selectinload(Game.away_team))
            .filter(Game.id == game_id)
            .first()
        )
        if game is None:
            return

        slots = [
            (game.home_team, "mandante"),
            (game.away_team, "visitante"),
        ]

        now = datetime.now(timezone.utc)

        for team, role in slots:
            result = generate_curiosity(game, team, role)

            existing = (
                db.query(GameCuriosity)
                .filter(GameCuriosity.game_id == game.id, GameCuriosity.role == role)
                .first()
            )
            if existing:
                existing.team_id = team.id
                existing.text = result["text"]
                existing.stat_source = result["stat_source"]
                existing.generated_at = now
            else:
                db.add(
                    GameCuriosity(
                        game_id=game.id,
                        team_id=team.id,
                        role=role,
                        text=result["text"],
                        stat_source=result["stat_source"],
                        stat_raw_value=None,
                        generated_at=now,
                    )
                )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def generate_for_all_games() -> None:
    from app.database import SessionLocal
    from app.modules.football.models import Game

    db: Session = SessionLocal()
    try:
        game_ids = [g.id for g in db.query(Game).all()]
    finally:
        db.close()

    for gid in game_ids:
        generate_for_game(gid)

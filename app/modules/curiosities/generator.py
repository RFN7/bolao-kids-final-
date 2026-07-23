import json
import logging
import time
import uuid
from datetime import datetime, timezone

import anthropic
from sqlalchemy.orm import Session, selectinload

from app.config import settings

logger = logging.getLogger(__name__)

_FALLBACK_CATALOG: dict[str, str] = {
    "Flamengo": "Um dos clubes mais vitoriosos do Brasil.",
    "Palmeiras": "Maior campeão do Brasileirão com 12 títulos.",
    "Corinthians": "Clube com uma das maiores torcidas do país.",
    "São Paulo": "Tricampeão mundial de clubes.",
}
_DEFAULT_TEXT = "Um dos grandes clubes do futebol brasileiro."

_MAX_TEXT_LEN = 160  # RN-30

_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """Você é um assistente educativo do Bolão Kids, um app de futebol para pais e filhos.
Gere UMA curiosidade curta sobre um time de futebol para o contexto de uma partida.

REGRAS OBRIGATÓRIAS:
- Máximo 15 palavras
- Tom animado e simples — uma criança de 7 anos deve entender
- Use APENAS os dados fornecidos — nunca invente estatísticas
- Nunca torça por nenhum time
- Nunca mencione apostas ou dinheiro
- Responda APENAS a curiosidade, sem explicação adicional"""

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=15.0,
            max_retries=1,
        )
    return _client


def generate_curiosity_with_ai(team_name: str, role: str, stats_json: str) -> str:
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY não configurada")

    user_prompt = (
        f"Time: {team_name}\n"
        f"Papel no jogo: {role} (mandante ou visitante)\n"
        f"Dados disponíveis: {stats_json}\n"
        "Gere uma curiosidade educativa sobre esse time para este jogo."
    )

    response = _get_client().messages.create(
        model=_MODEL,
        max_tokens=60,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = next((block.text for block in response.content if block.type == "text"), "").strip()

    if not text:
        raise ValueError("Claude retornou resposta vazia")

    if len(text) > _MAX_TEXT_LEN:
        text = text[:_MAX_TEXT_LEN]

    return text


def generate_curiosity(game, team, role: str) -> dict:
    stats_json = json.dumps({"nome": team.name, "pais": team.country}, ensure_ascii=False)

    start = time.monotonic()
    try:
        text = generate_curiosity_with_ai(team.name, role, stats_json)
        elapsed = time.monotonic() - start
        logger.info("Curiosidade [AI] para %s gerada em %.2fs", team.name, elapsed)
        stat_source = "ai"
    except Exception as exc:
        elapsed = time.monotonic() - start
        logger.warning(
            "Curiosidade [fallback] para %s após %.2fs (%s: %s)",
            team.name,
            elapsed,
            type(exc).__name__,
            exc,
        )
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

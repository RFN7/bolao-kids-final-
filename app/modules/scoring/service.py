import uuid

from sqlalchemy.orm import Session

from app.shared.exceptions import AppException


def _result(home: int, away: int) -> str:
    if home > away:
        return "home"
    if home < away:
        return "away"
    return "draw"


def calculate_points(home_pred: int, away_pred: int, home_real: int, away_real: int) -> int:
    if home_pred == home_real and away_pred == away_real:
        return 10
    if _result(home_pred, away_pred) == _result(home_real, away_real):
        return 5
    return 0


def apply_results(game_id: uuid.UUID) -> None:
    from app.database import SessionLocal
    from app.modules.families.models import FamilyStatistics
    from app.modules.football.models import Game
    from app.modules.predictions.models import Prediction

    db: Session = SessionLocal()
    round_id: uuid.UUID | None = None
    try:
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise AppException("GAME_NOT_FOUND", "Jogo não encontrado", 404)
        if game.status != "finished" or game.home_score is None or game.away_score is None:
            raise AppException("GAME_NOT_FINISHED", "Jogo não finalizado ou placar inválido", 400)

        round_id = game.round_id

        predictions = db.query(Prediction).filter(Prediction.game_id == game_id).all()

        family_preds: dict[uuid.UUID, dict[str, Prediction]] = {}
        for pred in predictions:
            pts = calculate_points(
                pred.home_score_pred,
                pred.away_score_pred,
                game.home_score,
                game.away_score,
            )
            pred.points_earned = pts
            if pred.family_id not in family_preds:
                family_preds[pred.family_id] = {}
            family_preds[pred.family_id][pred.author_type] = pred

        for family_id, preds_by_type in family_preds.items():
            stats = (
                db.query(FamilyStatistics)
                .filter(FamilyStatistics.family_id == family_id)
                .first()
            )
            if not stats:
                continue

            stats.games_played += 1

            for author_type, pred in preds_by_type.items():
                pts = pred.points_earned  # type: ignore[assignment]
                if author_type == "familia":
                    stats.total_points_family += pts
                    if pts == 10:
                        stats.exact_hits += 1
                    elif pts == 5:
                        stats.result_hits += 1
                elif author_type == "pai":
                    stats.total_points_pai += pts
                elif author_type == "filho":
                    stats.total_points_filho += pts

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if round_id is not None:
        from app.modules.ranking.service import save_ranking_snapshot
        save_ranking_snapshot(round_id)

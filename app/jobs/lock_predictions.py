from app.jobs.scheduler import scheduler


def _run_lock() -> None:
    from datetime import datetime, timezone

    from sqlalchemy.orm import Session

    from app.database import SessionLocal
    from app.modules.football.models import Game
    from app.modules.predictions.models import Prediction

    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        games_to_lock = (
            db.query(Game)
            .filter(Game.locks_at <= now, Game.status != "finished")
            .all()
        )
        if games_to_lock:
            game_ids = [g.id for g in games_to_lock]
            db.query(Prediction).filter(
                Prediction.game_id.in_(game_ids),
                Prediction.locked == False,  # noqa: E712
            ).update({"locked": True}, synchronize_session="fetch")
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def start() -> None:
    scheduler.add_job(_run_lock, "interval", minutes=1, id="lock_predictions", replace_existing=True)
    if not scheduler.running:
        scheduler.start()

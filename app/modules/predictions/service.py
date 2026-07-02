import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.families.models import Family
from app.modules.football.models import Game
from app.modules.predictions.models import Prediction
from app.modules.predictions.schemas import (
    GamePredictionsResponse,
    PredictionCreate,
    PredictionResponse,
    PredictionUpdate,
)
from app.shared.exceptions import AppException


def _get_family_owned_by(family_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> Family:
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family or family.user_id != user_id:
        raise AppException("FORBIDDEN", "Acesso negado a esta família", 403)
    return family


def create_prediction(user_id: uuid.UUID, data: PredictionCreate, db: Session) -> Prediction:
    _get_family_owned_by(data.family_id, user_id, db)

    game = db.query(Game).filter(Game.id == data.game_id).first()
    if not game:
        raise AppException("GAME_NOT_FOUND", "Jogo não encontrado", 404)

    if datetime.now(timezone.utc) >= game.locks_at:
        raise AppException("GAME_LOCKED", "Jogo encerrado para palpites", 423)

    existing = (
        db.query(Prediction)
        .filter(
            Prediction.family_id == data.family_id,
            Prediction.game_id == data.game_id,
            Prediction.author_type == data.author_type,
        )
        .first()
    )
    if existing:
        raise AppException("PREDICTION_ALREADY_EXISTS", "Palpite já registrado para este jogo/autor", 409)

    pred = Prediction(
        family_id=data.family_id,
        game_id=data.game_id,
        author_type=data.author_type,
        home_score_pred=data.home_score_pred,
        away_score_pred=data.away_score_pred,
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    return pred


def update_prediction(
    user_id: uuid.UUID, prediction_id: uuid.UUID, data: PredictionUpdate, db: Session
) -> Prediction:
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise AppException("NOT_FOUND", "Palpite não encontrado", 404)

    _get_family_owned_by(pred.family_id, user_id, db)

    if pred.locked:
        raise AppException("GAME_LOCKED", "Palpite travado — jogo encerrado para alterações", 423)

    pred.home_score_pred = data.home_score_pred
    pred.away_score_pred = data.away_score_pred
    pred.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pred)
    return pred


def get_game_predictions(
    user_id: uuid.UUID, game_id: uuid.UUID, family_id: uuid.UUID, db: Session
) -> GamePredictionsResponse:
    _get_family_owned_by(family_id, user_id, db)

    preds = (
        db.query(Prediction)
        .filter(Prediction.family_id == family_id, Prediction.game_id == game_id)
        .all()
    )

    pred_map = {p.author_type: PredictionResponse.model_validate(p) for p in preds}

    return GamePredictionsResponse(
        pai=pred_map.get("pai"),
        filho=pred_map.get("filho"),
        familia=pred_map.get("familia"),
        is_complete=len(preds) == 3,
    )

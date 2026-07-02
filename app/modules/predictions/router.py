import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.predictions import service
from app.modules.predictions.schemas import (
    GamePredictionsResponse,
    PredictionCreate,
    PredictionResponse,
    PredictionUpdate,
)

router = APIRouter(tags=["predictions"])


@router.post("/predictions", response_model=PredictionResponse, status_code=201)
def create_prediction(
    data: PredictionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.create_prediction(current_user.id, data, db)


@router.patch("/predictions/{prediction_id}", response_model=PredictionResponse)
def update_prediction(
    prediction_id: uuid.UUID,
    data: PredictionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.update_prediction(current_user.id, prediction_id, data, db)


@router.get("/games/{game_id}/predictions/me", response_model=GamePredictionsResponse)
def get_game_predictions(
    game_id: uuid.UUID,
    family_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.get_game_predictions(current_user.id, game_id, family_id, db)

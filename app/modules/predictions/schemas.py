import uuid
from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field


class PredictionCreate(BaseModel):
    family_id: uuid.UUID
    game_id: uuid.UUID
    author_type: Literal["pai", "filho", "familia"]
    home_score_pred: Annotated[int, Field(ge=0)]
    away_score_pred: Annotated[int, Field(ge=0)]


class PredictionUpdate(BaseModel):
    home_score_pred: Annotated[int, Field(ge=0)]
    away_score_pred: Annotated[int, Field(ge=0)]


class PredictionResponse(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    game_id: uuid.UUID
    author_type: str
    home_score_pred: int
    away_score_pred: int
    points_earned: Optional[int]
    locked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class GamePredictionsResponse(BaseModel):
    pai: Optional[PredictionResponse]
    filho: Optional[PredictionResponse]
    familia: Optional[PredictionResponse]
    is_complete: bool

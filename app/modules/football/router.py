from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.football import schemas, service

router = APIRouter(prefix="/games", tags=["football"])


@router.get("", response_model=list[schemas.GameResponse])
def list_games(
    round_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    return service.get_games(round_id, status, db)


@router.get("/{game_id}", response_model=schemas.GameResponse)
def get_game(game_id: UUID, db: Session = Depends(get_db)):
    return service.get_game(game_id, db)

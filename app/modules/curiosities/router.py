import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.modules.curiosities.models import GameCuriosity
from app.modules.curiosities.schemas import CuriositiesResponse, CuriosityResponse
from app.modules.football.service import get_game
from app.shared.exceptions import AppException

router = APIRouter(tags=["curiosities"])


@router.get("/games/{game_id}/curiosities", response_model=CuriositiesResponse)
def get_curiosities(game_id: uuid.UUID, db: Session = Depends(get_db)):
    # raises GAME_NOT_FOUND if game doesn't exist
    get_game(game_id, db)

    curios = (
        db.query(GameCuriosity)
        .options(selectinload(GameCuriosity.team))
        .filter(GameCuriosity.game_id == game_id)
        .order_by(GameCuriosity.role)
        .all()
    )

    if not curios:
        raise AppException(
            "CURIOSITIES_NOT_GENERATED",
            "Curiosidades ainda não foram geradas para este jogo",
            404,
        )

    return CuriositiesResponse(
        curiosities=[CuriosityResponse.model_validate(c) for c in curios]
    )

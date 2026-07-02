import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.families.models import Family
from app.modules.ranking import service
from app.modules.ranking.schemas import RankingHistoryResponse, RankingResponse
from app.shared.exceptions import AppException

router = APIRouter(tags=["ranking"])


@router.get("/ranking", response_model=RankingResponse)
def get_ranking(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.get_ranking(db, limit, offset)


@router.get("/ranking/history", response_model=RankingHistoryResponse)
def get_ranking_history(
    family_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise AppException("FAMILY_NOT_FOUND", "Família não encontrada", 404)
    if family.user_id != current_user.id:
        raise AppException("FORBIDDEN", "Acesso negado a esta família", 403)

    return service.get_ranking_history(family_id, db)

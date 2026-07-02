from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.families import schemas, service

router = APIRouter(prefix="/families", tags=["families"])


@router.post("", response_model=schemas.FamilyResponse, status_code=status.HTTP_201_CREATED)
def create_family(
    data: schemas.FamilyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.create_family(data, current_user, db)


@router.get("/me", response_model=list[schemas.FamilyResponse])
def list_families(
    status: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_families(current_user, status, db)


@router.patch("/{family_id}", response_model=schemas.FamilyResponse)
def update_family(
    family_id: UUID,
    data: schemas.FamilyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.update_family(family_id, data, current_user, db)

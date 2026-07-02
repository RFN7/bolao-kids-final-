from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth import schemas, service
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer()


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: schemas.RegisterRequest, db: Session = Depends(get_db)):
    return service.register_user(data, db)


@router.post("/login", response_model=schemas.TokenResponse)
def login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    return service.login_user(data.identifier, data.password, db)


@router.post("/refresh")
def refresh(data: schemas.RefreshRequest):
    return service.refresh_access_token(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    data: schemas.RefreshRequest,
    _: HTTPAuthorizationCredentials = Depends(_bearer),
):
    service.logout_user(data.refresh_token)


@router.post("/consent")
def consent(
    data: schemas.ConsentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.consented_at = datetime.now(timezone.utc)
    current_user.consent_version = data.consent_version
    db.commit()
    return {
        "consented_at": current_user.consented_at.isoformat(),
        "consent_version": current_user.consent_version,
    }

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.models import User
from app.security import verify_token
from app.shared.exceptions import AppException

_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    payload = verify_token(credentials.credentials)
    if not payload or payload.get("type") == "refresh":
        raise AppException("INVALID_TOKEN", "Token inválido ou expirado", 401)

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise AppException("USER_NOT_FOUND", "Usuário não encontrado", 404)

    return user

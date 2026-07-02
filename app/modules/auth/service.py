import uuid
from datetime import timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.cache import redis_client
from app.modules.auth.models import User
from app.modules.auth.schemas import RegisterRequest
from app.security import create_access_token, hash_password, verify_password, verify_token
from app.shared.exceptions import AppException

_ACCESS_MINUTES = 15
_REFRESH_DAYS = 30


def _issue_refresh_token(user_id: str) -> tuple[str, str]:
    jti = str(uuid.uuid4())
    token = create_access_token(
        {"sub": user_id, "type": "refresh", "jti": jti},
        expires_delta=timedelta(days=_REFRESH_DAYS),
    )
    return token, jti


def register_user(data: RegisterRequest, db: Session) -> User:
    if not data.email and not data.phone:
        raise AppException("VALIDATION_ERROR", "email ou phone é obrigatório", 422)

    if data.email and db.query(User).filter(User.email == data.email).first():
        raise AppException("EMAIL_ALREADY_EXISTS", "Email já cadastrado", 409)

    if data.phone and db.query(User).filter(User.phone == data.phone).first():
        raise AppException("PHONE_ALREADY_EXISTS", "Telefone já cadastrado", 409)

    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(identifier: str, password: str, db: Session) -> dict:
    user = db.query(User).filter(
        or_(User.email == identifier, User.phone == identifier)
    ).first()

    if not user or not verify_password(password, user.password_hash):
        raise AppException("INVALID_CREDENTIALS", "Credenciais inválidas", 401)

    access_token = create_access_token(
        {"sub": str(user.id)},
        expires_delta=timedelta(minutes=_ACCESS_MINUTES),
    )
    refresh_token, jti = _issue_refresh_token(str(user.id))
    redis_client.setex(f"rt:{jti}", timedelta(days=_REFRESH_DAYS), str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": _ACCESS_MINUTES * 60,
        "user": {"id": str(user.id), "name": user.name},
    }


def refresh_access_token(refresh_token: str) -> dict:
    payload = verify_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise AppException("INVALID_TOKEN", "Refresh token inválido", 401)

    jti = payload.get("jti")
    user_id = payload.get("sub")

    if not jti or not redis_client.exists(f"rt:{jti}"):
        raise AppException("TOKEN_REVOKED", "Refresh token revogado ou expirado", 401)

    access_token = create_access_token(
        {"sub": user_id},
        expires_delta=timedelta(minutes=_ACCESS_MINUTES),
    )
    return {"access_token": access_token, "expires_in": _ACCESS_MINUTES * 60}


def logout_user(refresh_token: str) -> None:
    payload = verify_token(refresh_token)
    if payload and payload.get("jti"):
        redis_client.delete(f"rt:{payload['jti']}")

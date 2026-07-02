import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.modules.auth.models import User
from app.modules.families.models import Child, Family, FamilyStatistics
from app.modules.families.schemas import FamilyCreate, FamilyUpdate
from app.shared.exceptions import AppException


def _generate_display_name(user_name: str) -> str:
    parts = user_name.strip().split()
    last = parts[-1] if len(parts) > 1 else parts[0] if parts else "Família"
    return f"Família {last}"


def _fetch_family(family_id: uuid.UUID, db: Session) -> Family:
    return (
        db.query(Family)
        .options(selectinload(Family.child))
        .filter(Family.id == family_id)
        .first()
    )


def create_family(data: FamilyCreate, user: User, db: Session) -> Family:
    if not user.consented_at:
        raise AppException("CONSENT_REQUIRED", "Consentimento LGPD obrigatório", 403)

    # Reutiliza criança existente com mesmo nome+birth_date do mesmo usuário (RN-06)
    existing_child_q = db.query(Child).filter(
        Child.user_id == user.id,
        Child.name == data.child.name,
    )
    if data.child.birth_date is not None:
        existing_child_q = existing_child_q.filter(Child.birth_date == data.child.birth_date)
    existing_child = existing_child_q.first()

    if existing_child:
        existing_family = db.query(Family).filter(Family.child_id == existing_child.id).first()
        if existing_family:
            raise AppException(
                "FAMILY_ALREADY_EXISTS_FOR_CHILD",
                "Esta criança já pertence a uma família",
                409,
            )
        child = existing_child
    else:
        child = Child(
            user_id=user.id,
            name=data.child.name,
            birth_date=data.child.birth_date,
            favorite_team_id=data.child.favorite_team_id,
        )
        db.add(child)
        db.flush()

    display_name = (data.display_name or "").strip() or _generate_display_name(user.name)

    family = Family(
        user_id=user.id,
        child_id=child.id,
        display_name=display_name,
        status="active",
    )
    db.add(family)
    db.flush()

    db.add(FamilyStatistics(family_id=family.id))
    db.commit()

    return _fetch_family(family.id, db)


def list_families(user: User, status: Optional[str], db: Session) -> list[Family]:
    q = (
        db.query(Family)
        .options(selectinload(Family.child))
        .filter(Family.user_id == user.id)
    )
    if status:
        q = q.filter(Family.status == status)
    return q.all()


def update_family(family_id: uuid.UUID, data: FamilyUpdate, user: User, db: Session) -> Family:
    family = db.query(Family).filter(Family.id == family_id).first()

    if not family:
        raise AppException("NOT_FOUND", "Família não encontrada", 404)
    if family.user_id != user.id:
        raise AppException("FORBIDDEN", "Acesso negado", 403)

    if data.display_name is not None:
        if data.display_name.strip() == "":
            raise AppException("VALIDATION_ERROR", "display_name não pode ser vazio", 422)
        family.display_name = data.display_name

    if data.status is not None:
        family.status = data.status

    family.updated_at = datetime.now(timezone.utc)
    db.commit()

    return _fetch_family(family.id, db)

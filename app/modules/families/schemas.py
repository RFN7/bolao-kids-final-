from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class ChildCreate(BaseModel):
    name: str
    birth_date: Optional[date] = None
    favorite_team_id: Optional[UUID] = None


class FamilyCreate(BaseModel):
    child: ChildCreate
    display_name: Optional[str] = None


class FamilyUpdate(BaseModel):
    display_name: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("active", "inactive"):
            raise ValueError("status deve ser 'active' ou 'inactive'")
        return v


class ChildResponse(BaseModel):
    id: UUID
    name: str
    birth_date: Optional[date] = None
    favorite_team_id: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FamilyResponse(BaseModel):
    id: UUID
    display_name: str
    status: str
    child: ChildResponse
    created_at: datetime

    model_config = {"from_attributes": True}

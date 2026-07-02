import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import VARCHAR, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(VARCHAR(120), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(VARCHAR(160), nullable=True, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(VARCHAR(20), nullable=True, unique=True)
    password_hash: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    consented_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    consent_version: Mapped[Optional[str]] = mapped_column(VARCHAR(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )

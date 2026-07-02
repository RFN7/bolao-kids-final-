import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import DATE, INTEGER, TIMESTAMP, VARCHAR, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Child(Base):
    __tablename__ = "children"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(VARCHAR(120), nullable=False)
    birth_date: Mapped[Optional[date]] = mapped_column(DATE(), nullable=True)
    favorite_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class Family(Base):
    __tablename__ = "families"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("children.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    display_name: Mapped[str] = mapped_column(VARCHAR(120), nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(20), server_default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )

    child: Mapped["Child"] = relationship("Child", foreign_keys=[child_id])


class FamilyStatistics(Base):
    __tablename__ = "family_statistics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    games_played: Mapped[int] = mapped_column(INTEGER(), server_default="0", nullable=False)
    exact_hits: Mapped[int] = mapped_column(INTEGER(), server_default="0", nullable=False)
    result_hits: Mapped[int] = mapped_column(INTEGER(), server_default="0", nullable=False)
    total_points_family: Mapped[int] = mapped_column(INTEGER(), server_default="0", nullable=False)
    total_points_pai: Mapped[int] = mapped_column(INTEGER(), server_default="0", nullable=False)
    total_points_filho: Mapped[int] = mapped_column(INTEGER(), server_default="0", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )

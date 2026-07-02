import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import DATE, SMALLINT, TIMESTAMP, VARCHAR, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    external_api_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(VARCHAR(120), nullable=False)
    short_name: Mapped[Optional[str]] = mapped_column(VARCHAR(40), nullable=True)
    crest_url: Mapped[Optional[str]] = mapped_column(VARCHAR, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(VARCHAR(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    external_api_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(VARCHAR(120), nullable=False)
    season: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    type: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    competition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(VARCHAR(80), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(DATE(), nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(DATE(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class Game(Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    external_api_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, unique=True)
    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rounds.id"), nullable=False
    )
    competition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False
    )
    home_team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False
    )
    away_team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False
    )
    kickoff_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    home_score: Mapped[Optional[int]] = mapped_column(SMALLINT(), nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(SMALLINT(), nullable=True)
    locks_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )

    home_team: Mapped["Team"] = relationship("Team", foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship("Team", foreign_keys=[away_team_id])

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import TIMESTAMP, VARCHAR, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GameCuriosity(Base):
    __tablename__ = "game_curiosities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(VARCHAR(10), nullable=False)
    text: Mapped[str] = mapped_column(VARCHAR(160), nullable=False)
    stat_source: Mapped[str] = mapped_column(VARCHAR(40), nullable=False)
    stat_raw_value: Mapped[Optional[dict]] = mapped_column(JSONB(), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    team: Mapped["Team"] = relationship(  # type: ignore[name-defined]
        "Team", foreign_keys=[team_id]
    )

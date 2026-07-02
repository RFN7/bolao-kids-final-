import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BOOLEAN, SMALLINT, TIMESTAMP, VARCHAR, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id"), nullable=False
    )
    author_type: Mapped[str] = mapped_column(VARCHAR(10), nullable=False)
    home_score_pred: Mapped[int] = mapped_column(SMALLINT(), nullable=False)
    away_score_pred: Mapped[int] = mapped_column(SMALLINT(), nullable=False)
    points_earned: Mapped[Optional[int]] = mapped_column(SMALLINT(), nullable=True)
    locked: Mapped[bool] = mapped_column(BOOLEAN(), server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )

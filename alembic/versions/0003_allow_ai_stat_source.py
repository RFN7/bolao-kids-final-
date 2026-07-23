"""Allow 'ai' as valid stat_source in game_curiosities

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-23

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_game_curiosities_stat_source", "game_curiosities", type_="check")
    op.create_check_constraint(
        "ck_game_curiosities_stat_source",
        "game_curiosities",
        "stat_source IN ('api', 'ai', 'fallback')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_game_curiosities_stat_source", "game_curiosities", type_="check")
    op.create_check_constraint(
        "ck_game_curiosities_stat_source",
        "game_curiosities",
        "stat_source IN ('api', 'fallback')",
    )

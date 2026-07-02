"""MVP tables

Revision ID: 0001
Revises:
Create Date: 2026-06-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.VARCHAR(120), nullable=False),
        sa.Column("email", sa.VARCHAR(160), nullable=True),
        sa.Column("phone", sa.VARCHAR(20), nullable=True),
        sa.Column("password_hash", sa.VARCHAR(255), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone"),
        sa.CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="ck_users_email_or_phone"),
    )

    # children
    op.create_table(
        "children",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(120), nullable=False),
        sa.Column("birth_date", sa.DATE(), nullable=True),
        sa.Column("favorite_team_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # teams
    op.create_table(
        "teams",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("external_api_id", sa.VARCHAR(50), nullable=False),
        sa.Column("name", sa.VARCHAR(120), nullable=False),
        sa.Column("short_name", sa.VARCHAR(40), nullable=True),
        sa.Column("crest_url", sa.TEXT(), nullable=True),
        sa.Column("country", sa.VARCHAR(60), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_api_id"),
    )

    # add FK from children to teams now that teams exists
    op.create_foreign_key(
        "fk_children_favorite_team",
        "children", "teams",
        ["favorite_team_id"], ["id"],
    )

    # families
    op.create_table(
        "families",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("child_id", sa.UUID(), nullable=False),
        sa.Column("display_name", sa.VARCHAR(120), nullable=False),
        sa.Column("status", sa.VARCHAR(20), server_default="active", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("child_id"),
        sa.UniqueConstraint("user_id", "child_id", name="uq_families_user_child"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_families_status"),
        sa.CheckConstraint("display_name != ''", name="ck_families_display_name_nonempty"),
    )

    # competitions
    op.create_table(
        "competitions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("external_api_id", sa.VARCHAR(50), nullable=False),
        sa.Column("name", sa.VARCHAR(120), nullable=False),
        sa.Column("season", sa.VARCHAR(20), nullable=False),
        sa.Column("type", sa.VARCHAR(20), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_api_id"),
        sa.CheckConstraint("type IN ('league', 'cup')", name="ck_competitions_type"),
    )

    # rounds
    op.create_table(
        "rounds",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("competition_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(80), nullable=False),
        sa.Column("start_date", sa.DATE(), nullable=True),
        sa.Column("end_date", sa.DATE(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["competition_id"], ["competitions.id"], ondelete="CASCADE"),
    )

    # games
    op.create_table(
        "games",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("external_api_id", sa.VARCHAR(50), nullable=False),
        sa.Column("round_id", sa.UUID(), nullable=False),
        sa.Column("competition_id", sa.UUID(), nullable=False),
        sa.Column("home_team_id", sa.UUID(), nullable=False),
        sa.Column("away_team_id", sa.UUID(), nullable=False),
        sa.Column("kickoff_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("status", sa.VARCHAR(20), nullable=False),
        sa.Column("home_score", sa.SMALLINT(), nullable=True),
        sa.Column("away_score", sa.SMALLINT(), nullable=True),
        sa.Column("locks_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_api_id"),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"]),
        sa.ForeignKeyConstraint(["competition_id"], ["competitions.id"]),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"]),
        sa.CheckConstraint("status IN ('scheduled', 'live', 'finished', 'postponed')", name="ck_games_status"),
        sa.CheckConstraint("home_team_id != away_team_id", name="ck_games_different_teams"),
    )

    op.create_index("ix_games_round_kickoff", "games", ["round_id", "kickoff_at"])
    op.create_index("ix_games_locks_at", "games", ["locks_at"])
    op.create_index("ix_games_status", "games", ["status"])

    # game_curiosities
    op.create_table(
        "game_curiosities",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("game_id", sa.UUID(), nullable=False),
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.VARCHAR(10), nullable=False),
        sa.Column("text", sa.VARCHAR(160), nullable=False),
        sa.Column("stat_source", sa.VARCHAR(40), nullable=False),
        sa.Column("stat_raw_value", JSONB(), nullable=True),
        sa.Column("generated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.UniqueConstraint("game_id", "role", name="uq_game_curiosities_game_role"),
        sa.CheckConstraint("role IN ('mandante', 'visitante')", name="ck_game_curiosities_role"),
        sa.CheckConstraint("stat_source IN ('api', 'fallback')", name="ck_game_curiosities_stat_source"),
    )

    # predictions
    op.create_table(
        "predictions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("family_id", sa.UUID(), nullable=False),
        sa.Column("game_id", sa.UUID(), nullable=False),
        sa.Column("author_type", sa.VARCHAR(10), nullable=False),
        sa.Column("home_score_pred", sa.SMALLINT(), nullable=False),
        sa.Column("away_score_pred", sa.SMALLINT(), nullable=False),
        sa.Column("points_earned", sa.SMALLINT(), nullable=True),
        sa.Column("locked", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.UniqueConstraint("family_id", "game_id", "author_type", name="uq_predictions_family_game_author"),
        sa.CheckConstraint("author_type IN ('pai', 'filho', 'familia')", name="ck_predictions_author_type"),
        sa.CheckConstraint("home_score_pred >= 0", name="ck_predictions_home_score_nn"),
        sa.CheckConstraint("away_score_pred >= 0", name="ck_predictions_away_score_nn"),
    )

    op.create_index("ix_predictions_game_id", "predictions", ["game_id"])
    op.create_index(
        "ix_predictions_game_familia",
        "predictions",
        ["game_id", "author_type"],
        postgresql_where=sa.text("author_type = 'familia'"),
    )

    # family_statistics
    op.create_table(
        "family_statistics",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("family_id", sa.UUID(), nullable=False),
        sa.Column("games_played", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("exact_hits", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("result_hits", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("total_points_family", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("total_points_pai", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("total_points_filho", sa.INTEGER(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("family_id"),
    )

    op.create_index(
        "ix_family_statistics_total_points",
        "family_statistics",
        [sa.text("total_points_family DESC")],
    )

    # ranking_snapshots
    op.create_table(
        "ranking_snapshots",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("round_id", sa.UUID(), nullable=False),
        sa.Column("family_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.INTEGER(), nullable=False),
        sa.Column("total_points_family", sa.INTEGER(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("round_id", "family_id", name="uq_ranking_snapshots_round_family"),
        sa.CheckConstraint("position >= 1", name="ck_ranking_snapshots_position"),
    )

    op.create_index("ix_ranking_snapshots_round_position", "ranking_snapshots", ["round_id", "position"])


def downgrade() -> None:
    op.drop_table("ranking_snapshots")

    op.drop_index("ix_family_statistics_total_points", table_name="family_statistics")
    op.drop_table("family_statistics")

    op.drop_index("ix_predictions_game_familia", table_name="predictions")
    op.drop_index("ix_predictions_game_id", table_name="predictions")
    op.drop_table("predictions")

    op.drop_table("game_curiosities")

    op.drop_index("ix_games_status", table_name="games")
    op.drop_index("ix_games_locks_at", table_name="games")
    op.drop_index("ix_games_round_kickoff", table_name="games")
    op.drop_table("games")

    op.drop_table("rounds")
    op.drop_table("competitions")
    op.drop_table("families")
    op.drop_foreign_key("fk_children_favorite_team", "children")
    op.drop_table("teams")
    op.drop_table("children")
    op.drop_table("users")

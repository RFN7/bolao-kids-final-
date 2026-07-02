"""Add consent fields to users

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("consented_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("users", sa.Column("consent_version", sa.VARCHAR(20), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "consent_version")
    op.drop_column("users", "consented_at")

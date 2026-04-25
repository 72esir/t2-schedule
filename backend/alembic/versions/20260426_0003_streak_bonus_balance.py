"""add streak bonus fields to users

Revision ID: 20260426_0003
Revises: 20260426_0002
Create Date: 2026-04-26 16:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260426_0003"
down_revision: Union[str, None] = "20260426_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("bonus_balance", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("streak_redeemed_count", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("users", "bonus_balance", server_default=None)
    op.alter_column("users", "streak_redeemed_count", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "streak_redeemed_count")
    op.drop_column("users", "bonus_balance")

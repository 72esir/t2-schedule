"""initial schema

Revision ID: 20260425_0001
Revises:
Create Date: 2026-04-25 00:00:01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260425_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role_enum = sa.Enum("manager", "user", name="userrole")
vacation_days_status_enum = sa.Enum(
    "pending",
    "approved",
    "rejected",
    "adjusted",
    name="vacationdaysstatus",
)
schedule_change_request_status_enum = sa.Enum(
    "pending",
    "approved",
    "rejected",
    name="schedulechangerequeststatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=True)
    vacation_days_status_enum.create(bind, checkfirst=True)
    schedule_change_request_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("registered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("alliance", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("role", user_role_enum, nullable=False, server_default="user"),
        sa.Column("vacation_days_declared", sa.Integer(), nullable=True),
        sa.Column("vacation_days_approved", sa.Integer(), nullable=True),
        sa.Column(
            "vacation_days_status",
            vacation_days_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_external_id"), "users", ["external_id"], unique=False)

    op.create_table(
        "collection_periods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alliance", sa.Text(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_collection_periods_id"), "collection_periods", ["id"], unique=False)
    op.create_index("idx_collection_periods_alliance", "collection_periods", ["alliance"], unique=False)

    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(op.f("ix_verification_tokens_id"), "verification_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_verification_tokens_token"), "verification_tokens", ["token"], unique=False)

    op.create_table(
        "schedule_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("work_days", sa.Integer(), nullable=False),
        sa.Column("rest_days", sa.Integer(), nullable=False),
        sa.Column("shift_start", sa.String(length=5), nullable=False),
        sa.Column("shift_end", sa.String(length=5), nullable=False),
        sa.Column("has_break", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("break_start", sa.String(length=5), nullable=True),
        sa.Column("break_end", sa.String(length=5), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedule_templates_id"), "schedule_templates", ["id"], unique=False)
    op.create_index("idx_schedule_templates_user_id", "schedule_templates", ["user_id"], unique=False)

    op.create_table(
        "schedule_change_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("period_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            schedule_change_request_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("employee_comment", sa.Text(), nullable=True),
        sa.Column("manager_comment", sa.Text(), nullable=True),
        sa.Column(
            "proposed_schedule",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("resolved_by_manager_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["period_id"], ["collection_periods.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_manager_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "period_id", name="uq_schedule_change_request_user_period"),
    )
    op.create_index(op.f("ix_schedule_change_requests_id"), "schedule_change_requests", ["id"], unique=False)
    op.create_index(
        "idx_schedule_change_requests_period_id",
        "schedule_change_requests",
        ["period_id"],
        unique=False,
    )
    op.create_index(
        "idx_schedule_change_requests_status",
        "schedule_change_requests",
        ["status"],
        unique=False,
    )

    op.create_table(
        "schedule_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("period_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=128), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["period_id"], ["collection_periods.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "period_id", "day", name="uq_schedule_user_period_day"),
    )
    op.create_index(op.f("ix_schedule_entries_id"), "schedule_entries", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_schedule_entries_id"), table_name="schedule_entries")
    op.drop_table("schedule_entries")

    op.drop_index("idx_schedule_change_requests_status", table_name="schedule_change_requests")
    op.drop_index("idx_schedule_change_requests_period_id", table_name="schedule_change_requests")
    op.drop_index(op.f("ix_schedule_change_requests_id"), table_name="schedule_change_requests")
    op.drop_table("schedule_change_requests")

    op.drop_index("idx_schedule_templates_user_id", table_name="schedule_templates")
    op.drop_index(op.f("ix_schedule_templates_id"), table_name="schedule_templates")
    op.drop_table("schedule_templates")

    op.drop_index(op.f("ix_verification_tokens_token"), table_name="verification_tokens")
    op.drop_index(op.f("ix_verification_tokens_id"), table_name="verification_tokens")
    op.drop_table("verification_tokens")

    op.drop_index("idx_collection_periods_alliance", table_name="collection_periods")
    op.drop_index(op.f("ix_collection_periods_id"), table_name="collection_periods")
    op.drop_table("collection_periods")

    op.drop_index(op.f("ix_users_external_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    schedule_change_request_status_enum.drop(bind, checkfirst=True)
    vacation_days_status_enum.drop(bind, checkfirst=True)
    user_role_enum.drop(bind, checkfirst=True)

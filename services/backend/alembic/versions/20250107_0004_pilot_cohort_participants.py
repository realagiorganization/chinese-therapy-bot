"""Add pilot cohort participants roster table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20250107_0004_pilot_cohort_participants"
down_revision = "20250105_0003_pilot_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pilot_cohort_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohort", sa.String(length=64), nullable=False),
        sa.Column("participant_alias", sa.String(length=64), nullable=True),
        sa.Column("contact_email", sa.String(length=254), nullable=True),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False, server_default="web"),
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="zh-CN"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="invited"),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("invite_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_received", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cohort", "contact_email", name="uq_pilot_cohort_email"),
        sa.UniqueConstraint("cohort", "contact_phone", name="uq_pilot_cohort_phone"),
    )
    op.create_index(
        "ix_pilot_cohort_participants_cohort",
        "pilot_cohort_participants",
        ["cohort"],
        unique=False,
    )
    op.create_index(
        "ix_pilot_cohort_participants_status",
        "pilot_cohort_participants",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_pilot_cohort_participants_channel",
        "pilot_cohort_participants",
        ["channel"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pilot_cohort_participants_channel",
        table_name="pilot_cohort_participants",
    )
    op.drop_index(
        "ix_pilot_cohort_participants_status",
        table_name="pilot_cohort_participants",
    )
    op.drop_index(
        "ix_pilot_cohort_participants_cohort",
        table_name="pilot_cohort_participants",
    )
    op.drop_table("pilot_cohort_participants")

"""Add pilot UAT sessions table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20250110_0005_pilot_uat_sessions"
down_revision = "20250107_0004_pilot_cohort_participants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pilot_uat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cohort", sa.String(length=64), nullable=False),
        sa.Column("participant_alias", sa.String(length=64), nullable=True),
        sa.Column("session_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("facilitator", sa.String(length=64), nullable=True),
        sa.Column("scenario", sa.String(length=64), nullable=True),
        sa.Column("environment", sa.String(length=32), nullable=True),
        sa.Column("platform", sa.String(length=24), nullable=True),
        sa.Column("device", sa.String(length=64), nullable=True),
        sa.Column("satisfaction_score", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("trust_score", sa.Integer(), nullable=True),
        sa.Column("highlights", sa.Text(), nullable=True),
        sa.Column("blockers", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("issues", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("action_items", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
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
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["pilot_cohort_participants.id"],
            name="fk_pilot_uat_participant",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pilot_uat_sessions_cohort_date",
        "pilot_uat_sessions",
        ["cohort", "session_date"],
        unique=False,
    )
    op.create_index(
        "ix_pilot_uat_sessions_participant",
        "pilot_uat_sessions",
        ["participant_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_pilot_uat_satisfaction_range",
        "pilot_uat_sessions",
        "satisfaction_score BETWEEN 1 AND 5",
    )
    op.create_check_constraint(
        "ck_pilot_uat_trust_range",
        "pilot_uat_sessions",
        "trust_score IS NULL OR (trust_score BETWEEN 1 AND 5)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_pilot_uat_trust_range", "pilot_uat_sessions", type_="check")
    op.drop_constraint("ck_pilot_uat_satisfaction_range", "pilot_uat_sessions", type_="check")
    op.drop_index(
        "ix_pilot_uat_sessions_participant",
        table_name="pilot_uat_sessions",
    )
    op.drop_index(
        "ix_pilot_uat_sessions_cohort_date",
        table_name="pilot_uat_sessions",
    )
    op.drop_table("pilot_uat_sessions")

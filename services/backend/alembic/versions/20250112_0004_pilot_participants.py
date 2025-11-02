"""Add pilot participant tracking and feedback linkage."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20250112_0004"
down_revision = "20250105_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pilot_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohort", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=True),
        sa.Column("preferred_name", sa.String(length=64), nullable=True),
        sa.Column("contact_email", sa.String(length=254), nullable=True),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="zh-CN"),
        sa.Column("timezone", sa.String(length=40), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False, server_default="web"),
        sa.Column("organization", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="prospect"),
        sa.Column("requires_follow_up", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("follow_up_notes", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metadata", sa.JSON(), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cohort", "contact_email", name="uq_pilot_participants_cohort_email"),
    )
    op.create_index(
        "ix_pilot_participants_cohort",
        "pilot_participants",
        ["cohort"],
        unique=False,
    )
    op.create_index(
        "ix_pilot_participants_status",
        "pilot_participants",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_pilot_participants_follow_up",
        "pilot_participants",
        ["requires_follow_up"],
        unique=False,
    )

    op.add_column(
        "pilot_feedback",
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_pilot_feedback_participant",
        "pilot_feedback",
        ["participant_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_pilot_feedback_participant_id",
        "pilot_feedback",
        "pilot_participants",
        ["participant_id"],
        ["id"],
        ondelete="set null",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_pilot_feedback_participant_id",
        "pilot_feedback",
        type_="foreignkey",
    )
    op.drop_index("ix_pilot_feedback_participant", table_name="pilot_feedback")
    op.drop_column("pilot_feedback", "participant_id")

    op.drop_index("ix_pilot_participants_follow_up", table_name="pilot_participants")
    op.drop_index("ix_pilot_participants_status", table_name="pilot_participants")
    op.drop_index("ix_pilot_participants_cohort", table_name="pilot_participants")
    op.drop_table("pilot_participants")

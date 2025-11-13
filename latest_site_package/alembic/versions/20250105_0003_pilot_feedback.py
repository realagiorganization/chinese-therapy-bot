"""Create pilot feedback table for UAT tracking."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20250105_0003_pilot_feedback"
down_revision = "20240704_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pilot_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cohort", sa.String(length=64), nullable=False),
        sa.Column("participant_alias", sa.String(length=64), nullable=True),
        sa.Column("contact_email", sa.String(length=254), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="participant"),
        sa.Column("channel", sa.String(length=32), nullable=False, server_default="web"),
        sa.Column("scenario", sa.String(length=64), nullable=True),
        sa.Column("sentiment_score", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("trust_score", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("usability_score", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("severity", sa.String(length=16), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("highlights", sa.Text(), nullable=True),
        sa.Column("blockers", sa.Text(), nullable=True),
        sa.Column("follow_up_needed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_pilot_feedback_user_id",
            ondelete="set null",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pilot_feedback_cohort", "pilot_feedback", ["cohort"], unique=False)
    op.create_index("ix_pilot_feedback_channel", "pilot_feedback", ["channel"], unique=False)
    op.create_index("ix_pilot_feedback_role", "pilot_feedback", ["role"], unique=False)
    op.create_index(
        "ix_pilot_feedback_submitted_at",
        "pilot_feedback",
        ["submitted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pilot_feedback_submitted_at", table_name="pilot_feedback")
    op.drop_index("ix_pilot_feedback_role", table_name="pilot_feedback")
    op.drop_index("ix_pilot_feedback_channel", table_name="pilot_feedback")
    op.drop_index("ix_pilot_feedback_cohort", table_name="pilot_feedback")
    op.drop_table("pilot_feedback")

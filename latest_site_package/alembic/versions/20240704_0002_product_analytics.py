"""Add analytics events table for product instrumentation."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20240704_0002"
down_revision = "20240618_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("funnel_stage", sa.String(length=32), nullable=True),
        sa.Column("properties", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_sessions.id"],
            name="fk_analytics_events_session_id",
            ondelete="set null",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_analytics_events_user_id",
            ondelete="set null",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analytics_events_type_time",
        "analytics_events",
        ["event_type", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_analytics_events_user_time",
        "analytics_events",
        ["user_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_analytics_events_stage_time",
        "analytics_events",
        ["funnel_stage", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_analytics_events_stage_time", table_name="analytics_events")
    op.drop_index("ix_analytics_events_user_time", table_name="analytics_events")
    op.drop_index("ix_analytics_events_type_time", table_name="analytics_events")
    op.drop_table("analytics_events")

"""Add mood check-in tracking for emotional trends."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20250214_0005"
down_revision = "20250112_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mood_check_ins",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("energy_level", sa.Integer(), nullable=True),
        sa.Column("emotion", sa.String(length=64), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("context", sa.JSON(), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "check_in_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="cascade"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("score >= 1 AND score <= 5", name="ck_mood_check_ins_score"),
        sa.CheckConstraint(
            "(energy_level IS NULL) OR (energy_level >= 1 AND energy_level <= 5)",
            name="ck_mood_check_ins_energy",
        ),
    )
    op.create_index(
        "ix_mood_check_ins_user",
        "mood_check_ins",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_mood_check_ins_user_check_in_at",
        "mood_check_ins",
        ["user_id", "check_in_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_mood_check_ins_user_check_in_at", table_name="mood_check_ins")
    op.drop_index("ix_mood_check_ins_user", table_name="mood_check_ins")
    op.drop_table("mood_check_ins")

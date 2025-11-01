"""Initial MindWell schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20240618_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("locale", sa.String(length=16), server_default="zh-CN", nullable=False),
        sa.Column("timezone", sa.String(length=40), server_default="Asia/Shanghai", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("phone_number", name="uq_users_phone"),
    )
    op.create_index("ix_users_external_id", "users", ["external_id"], unique=False)

    op.create_table(
        "feature_flags",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("rollout_percentage", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "updated_at",
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
        sa.CheckConstraint(
            "rollout_percentage >= 0 AND rollout_percentage <= 100",
            name="ck_feature_flags_rollout_range",
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "therapists",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("specialties", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("languages", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("price_per_session", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=8), server_default="CNY", nullable=False),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.Column("is_recommended", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("profile_image_url", sa.String(length=512), nullable=True),
        sa.Column("availability", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_therapists_slug"),
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("therapist_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_state", sa.String(length=32), server_default="active", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["therapist_id"],
            ["therapists.id"],
            name="fk_chat_sessions_therapist_id",
            ondelete="set null",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_chat_sessions_user_id",
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_sessions_user", "chat_sessions", ["user_id"], unique=False)

    op.create_table(
        "login_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_login_challenges_user_id",
            ondelete="set null",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_challenges_phone", "login_challenges", ["phone_number"], unique=False)
    op.create_index("ix_login_challenges_provider", "login_challenges", ["provider"], unique=False)

    op.create_table(
        "therapist_localizations",
        sa.Column("therapist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["therapist_id"],
            ["therapists.id"],
            name="fk_therapist_localizations_therapist_id",
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("therapist_id", "locale"),
    )
    op.create_index(
        "ix_therapist_localizations_locale",
        "therapist_localizations",
        ["locale"],
        unique=False,
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_sessions.id"],
            name="fk_chat_messages_session_id",
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_messages_session_idx",
        "chat_messages",
        ["session_id", "sequence_index"],
        unique=False,
    )

    op.create_table(
        "conversation_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("keywords", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_sessions.id"],
            name="fk_conversation_memories_session_id",
            ondelete="set null",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_conversation_memories_user_id",
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_conversation_memory_session"),
    )
    op.create_index(
        "ix_conversation_memories_user",
        "conversation_memories",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_memories_keywords",
        "conversation_memories",
        ["keywords"],
        unique=False,
        postgresql_using="gin",
    )

    op.create_table(
        "daily_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("spotlight", sa.String(length=280), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("mood_delta", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_daily_summaries_user_id",
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "summary_date", name="uq_daily_summary_day"),
    )
    op.create_index("ix_daily_summaries_user", "daily_summaries", ["user_id"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=256), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_refresh_tokens_user_id",
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user", "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "weekly_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("themes", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("highlights", sa.Text(), nullable=False),
        sa.Column("action_items", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("risk_level", sa.String(length=16), server_default="low", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_weekly_summaries_user_id",
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "week_start", name="uq_weekly_summary_week"),
    )
    op.create_index("ix_weekly_summaries_user", "weekly_summaries", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_weekly_summaries_user", table_name="weekly_summaries")
    op.drop_table("weekly_summaries")

    op.drop_index("ix_refresh_tokens_user", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("ix_daily_summaries_user", table_name="daily_summaries")
    op.drop_table("daily_summaries")

    op.drop_index("ix_conversation_memories_keywords", table_name="conversation_memories")
    op.drop_index("ix_conversation_memories_user", table_name="conversation_memories")
    op.drop_table("conversation_memories")

    op.drop_index("ix_chat_messages_session_idx", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_therapist_localizations_locale", table_name="therapist_localizations")
    op.drop_table("therapist_localizations")

    op.drop_index("ix_login_challenges_provider", table_name="login_challenges")
    op.drop_index("ix_login_challenges_phone", table_name="login_challenges")
    op.drop_table("login_challenges")

    op.drop_index("ix_chat_sessions_user", table_name="chat_sessions")
    op.drop_table("chat_sessions")

    op.drop_table("therapists")

    op.drop_table("feature_flags")

    op.drop_index("ix_users_external_id", table_name="users")
    op.drop_table("users")

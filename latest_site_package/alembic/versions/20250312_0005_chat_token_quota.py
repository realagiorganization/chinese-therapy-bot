"""Add chat token quota columns to users."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250312_0005_chat_token_quota"
down_revision = "20250215_0004_oauth2_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "chat_token_quota",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "chat_tokens_remaining",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_users_chat_token_quota_positive",
        "users",
        "chat_token_quota >= 0",
    )
    op.create_check_constraint(
        "ck_users_chat_tokens_remaining_positive",
        "users",
        "(chat_tokens_remaining IS NULL) OR (chat_tokens_remaining >= 0)",
    )
    op.execute(
        """
        UPDATE users
        SET chat_tokens_remaining = CASE
            WHEN chat_tokens_remaining IS NULL THEN chat_token_quota
            ELSE chat_tokens_remaining
        END
        """
    )
    op.alter_column("users", "chat_token_quota", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_users_chat_tokens_remaining_positive",
        "users",
        type_="check",
    )
    op.drop_constraint(
        "ck_users_chat_token_quota_positive",
        "users",
        type_="check",
    )
    op.drop_column("users", "chat_tokens_remaining")
    op.drop_column("users", "chat_token_quota")

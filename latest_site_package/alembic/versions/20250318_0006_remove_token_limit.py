"""Remove token_limit column from users."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250318_0006_remove_token_limit"
down_revision = "20250312_0005_chat_token_quota"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "token_limit")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_limit", sa.Integer(), nullable=False, server_default="3"),
    )
    op.execute("UPDATE users SET token_limit = 3 WHERE token_limit IS NULL")
    op.alter_column("users", "token_limit", server_default=None)

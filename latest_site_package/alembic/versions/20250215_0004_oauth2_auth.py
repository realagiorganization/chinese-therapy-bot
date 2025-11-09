"""Add oauth2 account metadata columns."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250215_0004_oauth2_auth"
down_revision = "20250105_0003_pilot_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("account_type", sa.String(length=16), nullable=False, server_default="legacy"),
    )
    op.add_column(
        "users",
        sa.Column("demo_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("token_limit", sa.Integer(), nullable=False, server_default="3"),
    )
    op.create_unique_constraint("uq_users_demo_code", "users", ["demo_code"])
    op.create_index("ix_users_account_type", "users", ["account_type"])

    op.execute("UPDATE users SET account_type = 'legacy' WHERE account_type IS NULL")
    op.execute("UPDATE users SET token_limit = 3 WHERE token_limit IS NULL")

    op.alter_column("users", "account_type", server_default=None)
    op.alter_column("users", "token_limit", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_users_account_type", table_name="users")
    op.drop_constraint("uq_users_demo_code", "users", type_="unique")
    op.drop_column("users", "token_limit")
    op.drop_column("users", "demo_code")
    op.drop_column("users", "account_type")

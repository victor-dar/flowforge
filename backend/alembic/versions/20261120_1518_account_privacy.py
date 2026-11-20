"""Add account privacy and verification state

Revision ID: 20261120_1518
Revises: 20261120_1115
"""

from alembic import op
import sqlalchemy as sa


revision = "20261120_1518"
down_revision = "20261120_1115"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "email_verified" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "email_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    op.drop_column("users", "email_verified")

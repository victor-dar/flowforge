"""Initial FlowForge schema

Revision ID: 20261120_1115
Revises:
"""

from alembic import op
import sqlalchemy as sa

from app.models import Base


revision = "20261120_1115"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    inspector = sa.inspect(bind)
    chatbot_columns = {
        column["name"]
        for column in inspector.get_columns("chatbots")
    }
    if "allowed_domains" not in chatbot_columns:
        op.add_column(
            "chatbots",
            sa.Column("allowed_domains", sa.Text(), nullable=False, server_default=""),
        )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

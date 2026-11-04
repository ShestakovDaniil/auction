"""Add backwards-compatible condition field and populate existing lots.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("lots", sa.Column("condition", sa.String(16), nullable=False, server_default="used"))


def downgrade():
    op.drop_column("lots", "condition")

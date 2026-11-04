"""Save lots per user, with a DB-level uniqueness rule.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "favorite_lots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("lots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "lot_id", name="uq_favorite_lots_user_lot"),
    )
    op.create_index("ix_favorite_lots_user_id", "favorite_lots", ["user_id"])
    op.create_index("ix_favorite_lots_lot_id", "favorite_lots", ["lot_id"])


def downgrade():
    op.drop_table("favorite_lots")

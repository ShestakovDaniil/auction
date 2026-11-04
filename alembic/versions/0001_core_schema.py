"""Create the original four Auction Lab tables.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("BUYER", "SELLER", "ADMIN", name="user_role"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "lots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "ACTIVE", "CLOSED", name="lot_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("start_price > 0", name="ck_lots_start_price_positive"),
    )
    op.create_index("ix_lots_id", "lots", ["id"])
    op.create_index("ix_lots_seller_id", "lots", ["seller_id"])
    op.create_table(
        "auctions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "ACTIVE", "CLOSED", name="auction_status"), nullable=False),
        sa.Column("current_price", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("current_price > 0", name="ck_auctions_current_price_positive"),
    )
    op.create_index("ix_auctions_id", "auctions", ["id"])
    op.create_index("ix_auctions_lot_id", "auctions", ["lot_id"])
    op.create_index("ix_auctions_end_time", "auctions", ["end_time"])
    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("auction_id", sa.Integer(), sa.ForeignKey("auctions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_sales_amount_positive"),
    )
    op.create_index("ix_sales_id", "sales", ["id"])
    op.create_index("ix_sales_auction_id", "sales", ["auction_id"])
    op.create_index("ix_sales_buyer_id", "sales", ["buyer_id"])


def downgrade():
    op.drop_table("sales")
    op.drop_table("auctions")
    op.drop_table("lots")
    op.drop_table("users")

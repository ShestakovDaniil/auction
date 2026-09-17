from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRole(str, Enum):
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"


class LotStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class AuctionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CLOSED = "closed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole, name="user_role"), default=UserRole.BUYER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    lots: Mapped[list["Lot"]] = relationship("Lot", back_populates="seller", cascade="all, delete-orphan")
    bids: Mapped[list["Bid"]] = relationship("Bid", back_populates="buyer", cascade="all, delete-orphan")


class Lot(Base):
    __tablename__ = "lots"
    __table_args__ = (CheckConstraint("start_price > 0", name="ck_lots_start_price_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[LotStatus] = mapped_column(SQLEnum(LotStatus, name="lot_status"), default=LotStatus.DRAFT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    seller: Mapped[User] = relationship("User", back_populates="lots")
    auctions: Mapped[list["Auction"]] = relationship(
        "Auction", back_populates="lot", cascade="all, delete-orphan", order_by="desc(Auction.start_time)"
    )


class Auction(Base):
    __tablename__ = "auctions"
    __table_args__ = (CheckConstraint("current_price > 0", name="ck_auctions_current_price_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    status: Mapped[AuctionStatus] = mapped_column(SQLEnum(AuctionStatus, name="auction_status"), default=AuctionStatus.PENDING, nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    lot: Mapped[Lot] = relationship("Lot", back_populates="auctions")
    bids: Mapped[list["Bid"]] = relationship(
        "Bid", back_populates="auction", cascade="all, delete-orphan", order_by="desc(Bid.created_at)"
    )


class Bid(Base):
    """Bid records are stored in the legacy `sales` table for DB compatibility."""

    __tablename__ = "sales"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_sales_amount_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    auction_id: Mapped[int] = mapped_column(ForeignKey("auctions.id", ondelete="RESTRICT"), nullable=False, index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    auction: Mapped[Auction] = relationship("Auction", back_populates="bids")
    buyer: Mapped[User] = relationship("User", back_populates="bids")


Sale = Bid

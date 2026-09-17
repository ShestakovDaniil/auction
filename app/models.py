from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRole(str, enum.Enum):
    BUYER = "buyer"
    SELLER = "seller"
    BOTH = "both"


class LotStatus(str, enum.Enum):
    OPEN = "open"
    SOLD = "sold"
    UNSOLD = "unsold"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(190), nullable=False, unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    organized_auctions: Mapped[list[Auction]] = relationship(back_populates="organizer")
    selling_lots: Mapped[list[Lot]] = relationship(back_populates="seller")
    bids: Mapped[list[Bid]] = relationship(back_populates="buyer")


class Auction(Base):
    __tablename__ = "auctions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    organizer: Mapped[User] = relationship(back_populates="organized_auctions")
    lots: Mapped[list[Lot]] = relationship(back_populates="auction", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_auction_period", "starts_at", "ends_at"),)


class Lot(Base):
    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    auction_id: Mapped[int] = mapped_column(ForeignKey("auctions.id", ondelete="CASCADE"), nullable=False, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    min_increment: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("1.00"))
    status: Mapped[LotStatus] = mapped_column(Enum(LotStatus), nullable=False, default=LotStatus.OPEN, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    auction: Mapped[Auction] = relationship(back_populates="lots")
    seller: Mapped[User] = relationship(back_populates="selling_lots")
    bids: Mapped[list[Bid]] = relationship(back_populates="lot", cascade="all, delete-orphan")
    sale: Mapped[Sale | None] = relationship(back_populates="lot", uselist=False)


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id", ondelete="CASCADE"), nullable=False, index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)

    lot: Mapped[Lot] = relationship(back_populates="bids")
    buyer: Mapped[User] = relationship(back_populates="bids")

    __table_args__ = (Index("ix_bid_lot_amount", "lot_id", "amount"),)


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False, unique=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    final_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sold_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)

    lot: Mapped[Lot] = relationship(back_populates="sale")
    buyer: Mapped[User] = relationship(foreign_keys=[buyer_id])
    seller: Mapped[User] = relationship(foreign_keys=[seller_id])

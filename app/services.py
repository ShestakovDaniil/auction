from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain import DomainRuleError, minimum_allowed_bid, validate_bid_amount, validate_bid_window
from app.models import Auction, Bid, Lot, LotStatus, Sale, User, UserRole
from app.schemas import AuctionCreate, BidCreate, LotCreate, UserCreate


def _not_found(name: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found")


def create_user(db: Session, data: UserCreate) -> User:
    user = User(name=data.name, email=str(data.email), role=data.role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="User with this email already exists") from exc
    db.refresh(user)
    return user


def create_auction(db: Session, data: AuctionCreate) -> Auction:
    organizer = db.get(User, data.organizer_id)
    if not organizer:
        raise _not_found("Organizer")
    if organizer.role not in {UserRole.SELLER, UserRole.BOTH}:
        raise HTTPException(status_code=422, detail="Organizer must have seller role")

    auction = Auction(**data.model_dump())
    db.add(auction)
    db.commit()
    db.refresh(auction)
    return auction


def create_lot(db: Session, auction_id: int, data: LotCreate) -> Lot:
    auction = db.get(Auction, auction_id)
    if not auction:
        raise _not_found("Auction")
    if datetime.now() >= auction.ends_at:
        raise HTTPException(status_code=422, detail="Cannot add a lot to an ended auction")

    seller = db.get(User, data.seller_id)
    if not seller:
        raise _not_found("Seller")
    if seller.role not in {UserRole.SELLER, UserRole.BOTH}:
        raise HTTPException(status_code=422, detail="User must have seller role")

    lot = Lot(auction_id=auction_id, **data.model_dump())
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


def current_price(db: Session, lot: Lot) -> Decimal:
    highest = db.scalar(select(func.max(Bid.amount)).where(Bid.lot_id == lot.id))
    return Decimal(highest) if highest is not None else Decimal(lot.start_price)


def place_bid(db: Session, lot_id: int, data: BidCreate) -> Bid:
    # Row lock serializes competing bids for the same lot in MariaDB/InnoDB.
    lot = db.scalar(select(Lot).where(Lot.id == lot_id).with_for_update())
    if not lot:
        db.rollback()
        raise _not_found("Lot")
    if lot.status != LotStatus.OPEN:
        db.rollback()
        raise HTTPException(status_code=422, detail="Lot is already closed")

    auction = db.get(Auction, lot.auction_id)
    if not auction:
        db.rollback()
        raise _not_found("Auction")

    buyer = db.get(User, data.buyer_id)
    if not buyer:
        db.rollback()
        raise _not_found("Buyer")
    if buyer.role not in {UserRole.BUYER, UserRole.BOTH}:
        db.rollback()
        raise HTTPException(status_code=422, detail="User must have buyer role")
    if lot.seller_id == buyer.id:
        db.rollback()
        raise HTTPException(status_code=422, detail="Seller cannot bid on own lot")

    highest = db.scalar(select(func.max(Bid.amount)).where(Bid.lot_id == lot_id))
    minimum = minimum_allowed_bid(
        Decimal(lot.start_price),
        Decimal(lot.min_increment),
        Decimal(highest) if highest is not None else None,
    )

    try:
        validate_bid_window(datetime.now(), auction.starts_at, auction.ends_at)
        validate_bid_amount(Decimal(data.amount), minimum)
    except DomainRuleError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    bid = Bid(lot_id=lot_id, buyer_id=data.buyer_id, amount=data.amount)
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid


def close_lot(db: Session, lot_id: int) -> Sale | None:
    lot = db.scalar(select(Lot).where(Lot.id == lot_id).with_for_update())
    if not lot:
        db.rollback()
        raise _not_found("Lot")
    if lot.status != LotStatus.OPEN:
        db.rollback()
        raise HTTPException(status_code=422, detail="Lot is already closed")

    auction = db.get(Auction, lot.auction_id)
    if not auction:
        db.rollback()
        raise _not_found("Auction")
    if datetime.now() < auction.ends_at:
        db.rollback()
        raise HTTPException(status_code=422, detail="Lot can be closed only after the auction ends")

    highest_bid = db.scalar(
        select(Bid)
        .where(Bid.lot_id == lot_id)
        .order_by(Bid.amount.desc(), Bid.created_at.asc())
        .limit(1)
    )

    if highest_bid is None:
        lot.status = LotStatus.UNSOLD
        db.commit()
        return None

    sale = Sale(
        lot_id=lot.id,
        buyer_id=highest_bid.buyer_id,
        seller_id=lot.seller_id,
        final_price=highest_bid.amount,
    )
    lot.status = LotStatus.SOLD
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale

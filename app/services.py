from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.access import get_owned_lot
from app.auth import hash_password
from app.config import get_settings
from app.models import Auction, AuctionStatus, Bid, Lot, LotStatus, User, UserRole
from app.schemas import AuctionCreate, BidCreate, LotCreate, UserCreate

settings = get_settings()
MONEY = Decimal("0.01")


def as_money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def create_user(db: Session, data: UserCreate) -> User:
    if data.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Регистрация администратора через публичный интерфейс запрещена")

    username = data.username.strip()
    email = str(data.email).strip().lower()
    existing = db.scalar(select(User).where(or_(User.username == username, User.email == email)))
    if existing:
        raise HTTPException(status_code=409, detail="Логин или email уже занят")

    user = User(username=username, email=email, hashed_password=hash_password(data.password), role=data.role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Логин или email уже занят") from exc
    db.refresh(user)
    return user


def create_lot(db: Session, owner: User, data: LotCreate) -> Lot:
    if owner.role not in {UserRole.SELLER, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Создавать лоты может только продавец")
    lot = Lot(
        title=data.title.strip(),
        description=(data.description or "").strip() or None,
        start_price=as_money(data.start_price),
        seller_id=owner.id,
        status=LotStatus.DRAFT,
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


def _validate_auction_window(start_time: datetime, end_time: datetime) -> None:
    if end_time <= start_time:
        raise HTTPException(status_code=422, detail="Окончание аукциона должно быть позже начала")


def create_auction(db: Session, owner: User, data: AuctionCreate) -> Auction:
    if owner.role not in {UserRole.SELLER, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Создавать аукционы может только продавец")
    _validate_auction_window(data.start_time, data.end_time)

    lot = get_owned_lot(db, owner, data.lot_id, lock=True)
    existing = db.scalar(
        select(Auction).where(
            Auction.lot_id == lot.id,
            Auction.status.in_([AuctionStatus.PENDING, AuctionStatus.ACTIVE]),
        )
    )
    if existing:
        db.rollback()
        raise HTTPException(status_code=409, detail="Для этого лота уже есть незавершённый аукцион")

    now = datetime.now()
    if data.end_time <= now:
        db.rollback()
        raise HTTPException(status_code=422, detail="Нельзя создать уже завершившийся аукцион")
    initial_status = AuctionStatus.PENDING if data.start_time > now else AuctionStatus.ACTIVE
    auction = Auction(
        lot_id=lot.id,
        start_time=data.start_time,
        end_time=data.end_time,
        status=initial_status,
        current_price=as_money(lot.start_price),
    )
    lot.status = LotStatus.ACTIVE
    db.add(auction)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Не удалось создать аукцион из-за конфликта данных") from exc
    db.refresh(auction)
    return auction


def highest_bid(db: Session, auction_id: int) -> Bid | None:
    return db.scalar(
        select(Bid)
        .where(Bid.auction_id == auction_id)
        .order_by(Bid.amount.desc(), Bid.created_at.asc(), Bid.id.asc())
        .limit(1)
    )


def synchronize_auction_statuses(db: Session) -> int:
    now = datetime.now()
    changed = 0
    pending = db.scalars(
        select(Auction).options(joinedload(Auction.lot)).where(
            Auction.status == AuctionStatus.PENDING,
            Auction.start_time <= now,
        )
    ).all()
    for auction in pending:
        if auction.end_time is not None and auction.end_time <= now:
            auction.status = AuctionStatus.CLOSED
            auction.lot.status = LotStatus.CLOSED
        else:
            auction.status = AuctionStatus.ACTIVE
        changed += 1

    expired = db.scalars(
        select(Auction).options(joinedload(Auction.lot)).where(
            Auction.status == AuctionStatus.ACTIVE,
            Auction.end_time.is_not(None),
            Auction.end_time <= now,
        )
    ).all()
    for auction in expired:
        auction.status = AuctionStatus.CLOSED
        auction.lot.status = LotStatus.CLOSED
        changed += 1
    if changed:
        db.commit()
    return changed


def minimum_bid_for_auction(db: Session, auction: Auction) -> Decimal:
    bid_count = db.scalar(select(func.count(Bid.id)).where(Bid.auction_id == auction.id)) or 0
    current = as_money(auction.current_price)
    return current if bid_count == 0 else current + as_money(settings.min_bid_increment)


def place_bid(db: Session, buyer: User, auction_id: int, data: BidCreate) -> Bid:
    if buyer.role not in {UserRole.BUYER, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Ставки доступны покупателям")

    auction = db.scalar(
        select(Auction)
        .options(joinedload(Auction.lot))
        .where(Auction.id == auction_id)
        .with_for_update()
    )
    if not auction:
        db.rollback()
        raise HTTPException(status_code=404, detail="Аукцион не найден")

    now = datetime.now()
    if auction.status == AuctionStatus.PENDING and auction.start_time <= now:
        auction.status = AuctionStatus.ACTIVE
    if auction.end_time is not None and auction.end_time <= now:
        auction.status = AuctionStatus.CLOSED
        auction.lot.status = LotStatus.CLOSED
        db.commit()
        raise HTTPException(status_code=409, detail="Аукцион уже завершён")
    if auction.status != AuctionStatus.ACTIVE or auction.start_time > now:
        db.rollback()
        raise HTTPException(status_code=409, detail="Аукцион сейчас не принимает ставки")
    if auction.lot.seller_id == buyer.id:
        db.rollback()
        raise HTTPException(status_code=403, detail="Нельзя делать ставку на собственный лот")

    amount = as_money(data.amount)
    minimum = minimum_bid_for_auction(db, auction)
    if amount < minimum:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Минимальная следующая ставка: {minimum:.2f} ₽")

    bid = Bid(auction_id=auction.id, buyer_id=buyer.id, amount=amount)
    auction.current_price = amount
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid


def close_auction(db: Session, owner: User, auction_id: int) -> Auction:
    auction = db.scalar(
        select(Auction)
        .options(joinedload(Auction.lot))
        .where(Auction.id == auction_id)
        .with_for_update()
    )
    if not auction:
        db.rollback()
        raise HTTPException(status_code=404, detail="Аукцион не найден")
    if auction.lot.seller_id != owner.id and owner.role != UserRole.ADMIN:
        db.rollback()
        raise HTTPException(status_code=404, detail="Аукцион не найден")
    if auction.status == AuctionStatus.CLOSED:
        db.rollback()
        raise HTTPException(status_code=409, detail="Аукцион уже завершён")

    auction.status = AuctionStatus.CLOSED
    auction.end_time = datetime.now()
    auction.lot.status = LotStatus.CLOSED
    db.commit()
    db.refresh(auction)
    return auction

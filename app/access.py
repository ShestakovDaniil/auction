from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Auction, Bid, Lot, LotStatus, User, UserRole


def get_visible_lot(db: Session, user: User, lot_id: int) -> Lot:
    lot = db.scalar(select(Lot).where(Lot.id == lot_id))
    if not lot:
        raise HTTPException(status_code=404, detail="Лот не найден")
    if lot.status == LotStatus.DRAFT and lot.seller_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Лот не найден")
    return lot


def get_owned_lot(db: Session, user: User, lot_id: int, *, lock: bool = False) -> Lot:
    statement = select(Lot).where(Lot.id == lot_id)
    if lock:
        statement = statement.with_for_update()
    lot = db.scalar(statement)
    if not lot:
        raise HTTPException(status_code=404, detail="Лот не найден")
    if lot.seller_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Лот не найден")
    return lot


def get_visible_auction(db: Session, user: User, auction_id: int) -> Auction:
    auction = db.scalar(
        select(Auction)
        .options(joinedload(Auction.lot).joinedload(Lot.seller))
        .where(Auction.id == auction_id)
    )
    if not auction:
        raise HTTPException(status_code=404, detail="Аукцион не найден")
    if auction.lot.status == LotStatus.DRAFT and auction.lot.seller_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="Аукцион не найден")
    return auction


def can_view_bid_history(db: Session, user: User, lot: Lot) -> bool:
    if user.role == UserRole.ADMIN or lot.seller_id == user.id:
        return True
    auction_ids = select(Auction.id).where(Auction.lot_id == lot.id)
    return db.scalar(
        select(Bid.id).where(Bid.auction_id.in_(auction_ids), Bid.buyer_id == user.id).limit(1)
    ) is not None

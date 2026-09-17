from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.models import Bid, Lot, User
from app.schemas import BidCreate, BidRead, LotCreate, LotRead
from app.services import create_lot, place_bid

router = APIRouter(prefix="/api/lots", tags=["lots"])


@router.get("/{lot_id}", response_model=LotRead)
def get_lot(lot_id: int, db: Session = Depends(get_db)):
    lot = db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Лот не найден")
    return lot


@router.post("", response_model=LotRead, status_code=201)
def add_lot(
    payload: LotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    return create_lot(db, current_user, payload)


@router.get("/{lot_id}/bids", response_model=list[BidRead])
def list_bids(lot_id: int, db: Session = Depends(get_db)):
    lot = db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Лот не найден")
    auction_ids = [auction.id for auction in lot.auctions]
    if not auction_ids:
        return []
    return db.scalars(
        select(Bid)
        .where(Bid.auction_id.in_(auction_ids))
        .order_by(Bid.created_at.desc())
    ).all()


@router.post("/auctions/{auction_id}/bids", response_model=BidRead, status_code=201)
def add_bid(
    auction_id: int,
    payload: BidCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    return place_bid(db, current_user, auction_id, payload)

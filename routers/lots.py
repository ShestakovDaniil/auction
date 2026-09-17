from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Bid, Lot
from app.schemas import BidCreate, BidRead, LotRead, SaleRead
from app.services import close_lot, place_bid

router = APIRouter(prefix="/api/lots", tags=["lots"])


@router.get("/{lot_id}", response_model=LotRead)
def get_lot(lot_id: int, db: Session = Depends(get_db)):
    lot = db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    return lot


@router.get("/{lot_id}/bids", response_model=list[BidRead])
def list_bids(lot_id: int, db: Session = Depends(get_db)):
    if not db.get(Lot, lot_id):
        raise HTTPException(status_code=404, detail="Lot not found")
    return db.scalars(
        select(Bid).where(Bid.lot_id == lot_id).order_by(Bid.amount.desc(), Bid.created_at.asc())
    ).all()


@router.post("/{lot_id}/bids", response_model=BidRead, status_code=201)
def add_bid(lot_id: int, payload: BidCreate, db: Session = Depends(get_db)):
    return place_bid(db, lot_id, payload)


@router.post("/{lot_id}/close", response_model=SaleRead | None)
def finish_lot(lot_id: int, db: Session = Depends(get_db)):
    return close_lot(db, lot_id)

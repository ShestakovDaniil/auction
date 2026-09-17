from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Auction, Lot
from app.schemas import AuctionCreate, AuctionRead, LotCreate, LotRead
from app.services import create_auction, create_lot

router = APIRouter(prefix="/api/auctions", tags=["auctions"])


@router.get("", response_model=list[AuctionRead])
def list_auctions(db: Session = Depends(get_db)):
    return db.scalars(select(Auction).order_by(Auction.starts_at.desc())).all()


@router.post("", response_model=AuctionRead, status_code=201)
def add_auction(payload: AuctionCreate, db: Session = Depends(get_db)):
    return create_auction(db, payload)


@router.get("/{auction_id}", response_model=AuctionRead)
def get_auction(auction_id: int, db: Session = Depends(get_db)):
    auction = db.get(Auction, auction_id)
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    return auction


@router.get("/{auction_id}/lots", response_model=list[LotRead])
def list_lots(auction_id: int, db: Session = Depends(get_db)):
    if not db.get(Auction, auction_id):
        raise HTTPException(status_code=404, detail="Auction not found")
    return db.scalars(select(Lot).where(Lot.auction_id == auction_id).order_by(Lot.id)).all()


@router.post("/{auction_id}/lots", response_model=LotRead, status_code=201)
def add_lot(auction_id: int, payload: LotCreate, db: Session = Depends(get_db)):
    return create_lot(db, auction_id, payload)

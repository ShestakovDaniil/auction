from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_current_user
from app.db import get_db
from app.models import Auction, Lot, User
from app.schemas import AuctionCreate, AuctionRead
from app.services import close_auction, create_auction, synchronize_auction_statuses

router = APIRouter(prefix="/api/auctions", tags=["auctions"])


@router.get("", response_model=list[AuctionRead])
def list_auctions(db: Session = Depends(get_db)):
    synchronize_auction_statuses(db)
    return db.scalars(select(Auction).order_by(Auction.start_time.desc())).all()


@router.get("/{auction_id}", response_model=AuctionRead)
def get_auction(auction_id: int, db: Session = Depends(get_db)):
    synchronize_auction_statuses(db)
    auction = db.get(Auction, auction_id)
    if not auction:
        raise HTTPException(status_code=404, detail="Аукцион не найден")
    return auction


@router.post("", response_model=AuctionRead, status_code=201)
def add_auction(
    payload: AuctionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    return create_auction(db, current_user, payload)


@router.post("/{auction_id}/close", response_model=AuctionRead)
def finish_auction(
    auction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    return close_auction(db, current_user, auction_id)

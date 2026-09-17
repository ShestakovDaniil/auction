from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import can_view_bid_history, get_visible_lot
from app.auth import require_current_user
from app.db import get_db
from app.models import Auction, Bid, User
from app.schemas import BidRead

router = APIRouter(prefix="/api/lots", tags=["api: bids"])


@router.get("/{lot_id}/bids", response_model=list[BidRead])
def list_bids(lot_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_current_user)):
    lot = get_visible_lot(db, current_user, lot_id)
    if not can_view_bid_history(db, current_user, lot):
        raise HTTPException(status_code=403, detail="История ставок этого лота недоступна")
    auction_ids = select(Auction.id).where(Auction.lot_id == lot.id)
    return db.scalars(select(Bid).where(Bid.auction_id.in_(auction_ids)).order_by(Bid.created_at.desc())).all()

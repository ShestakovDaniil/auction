from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.models import Auction, User
from app.schemas import AuctionRead
from app.services import synchronize_auction_statuses

router = APIRouter(prefix="/api/auctions", tags=["api: auctions"])


@router.get("", response_model=list[AuctionRead])
def list_auctions(db: Session = Depends(get_db), _current_user: User = Depends(require_current_user)):
    synchronize_auction_statuses(db)
    return db.scalars(select(Auction).order_by(Auction.start_time.desc())).all()

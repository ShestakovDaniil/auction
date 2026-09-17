from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.access import get_visible_auction
from app.auth import require_current_user
from app.db import get_db
from app.models import User
from app.schemas import AuctionRead
from app.services import synchronize_auction_statuses

router = APIRouter(prefix="/api/auctions", tags=["api: auctions"])


@router.get("/{auction_id}", response_model=AuctionRead)
def get_auction(auction_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_current_user)):
    synchronize_auction_statuses(db)
    return get_visible_auction(db, current_user, auction_id)

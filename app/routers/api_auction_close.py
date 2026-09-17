from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.models import User
from app.schemas import AuctionRead
from app.security import require_api_csrf
from app.services import close_auction

router = APIRouter(prefix="/api/auctions", tags=["api: auctions"])


@router.post("/{auction_id}/close", response_model=AuctionRead, dependencies=[Depends(require_api_csrf)])
def finish_auction(auction_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_current_user)):
    return close_auction(db, current_user, auction_id)

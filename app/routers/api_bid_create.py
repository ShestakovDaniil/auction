from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.models import User
from app.schemas import BidCreate, BidRead
from app.security import require_api_csrf
from app.services import place_bid

router = APIRouter(prefix="/api/auctions", tags=["api: bids"])


@router.post("/{auction_id}/bids", response_model=BidRead, status_code=201, dependencies=[Depends(require_api_csrf)])
def add_bid(auction_id: int, payload: BidCreate, db: Session = Depends(get_db), current_user: User = Depends(require_current_user)):
    return place_bid(db, current_user, auction_id, payload)

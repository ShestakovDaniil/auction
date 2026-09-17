from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.models import User
from app.schemas import AuctionCreate, AuctionRead
from app.security import require_api_csrf
from app.services import create_auction

router = APIRouter(prefix="/api/auctions", tags=["api: auctions"])


@router.post("", response_model=AuctionRead, status_code=201, dependencies=[Depends(require_api_csrf)])
def add_auction(payload: AuctionCreate, db: Session = Depends(get_db), current_user: User = Depends(require_current_user)):
    return create_auction(db, current_user, payload)

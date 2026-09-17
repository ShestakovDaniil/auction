from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.db import get_db
from app.models import Auction, Bid, Lot, User, UserRole

router = APIRouter(prefix="/api/reports", tags=["api: reports"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), _admin: User = Depends(require_roles(UserRole.ADMIN))):
    return {
        "users": db.scalar(select(func.count(User.id))) or 0,
        "lots": db.scalar(select(func.count(Lot.id))) or 0,
        "auctions": db.scalar(select(func.count(Auction.id))) or 0,
        "bids": db.scalar(select(func.count(Bid.id))) or 0,
    }

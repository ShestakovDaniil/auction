"""Compatibility API for the old `sales` module.

The old project stored bids in the `sales` table. The fixed build keeps that table
for DB compatibility, while exposing the records consistently as bids.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.models import Auction, Bid, Lot, User

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_current_user),
):
    return {
        "users": db.scalar(select(func.count(User.id))) or 0,
        "lots": db.scalar(select(func.count(Lot.id))) or 0,
        "auctions": db.scalar(select(func.count(Auction.id))) or 0,
        "bids": db.scalar(select(func.count(Bid.id))) or 0,
    }

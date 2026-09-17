from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_current_user
from app.db import get_db
from app.http import template_context, templates
from app.models import Auction, AuctionStatus, Bid, Lot, User, UserRole
from app.services import highest_bid, synchronize_auction_statuses

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse, tags=["web"])
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    synchronize_auction_statuses(db)
    seller_rows = []
    if current_user.role in {UserRole.SELLER, UserRole.ADMIN}:
        lots = db.query(Lot).options(joinedload(Lot.auctions)).filter(Lot.seller_id == current_user.id).order_by(Lot.created_at.desc()).all()
        seller_rows = [{"lot": lot, "auction": lot.auctions[0] if lot.auctions else None} for lot in lots]

    buyer_bids = []
    if current_user.role in {UserRole.BUYER, UserRole.ADMIN}:
        buyer_bids = db.query(Bid).options(joinedload(Bid.auction).joinedload(Auction.lot)).filter(Bid.buyer_id == current_user.id).order_by(Bid.created_at.desc()).limit(25).all()

    available_auctions = db.query(Auction).options(joinedload(Auction.lot).joinedload(Lot.seller)).filter(Auction.status == AuctionStatus.ACTIVE).order_by(Auction.end_time.is_(None), Auction.end_time.asc()).limit(6).all()
    available_auctions = [auction for auction in available_auctions if auction.lot.seller_id != current_user.id]

    won_count = 0
    if current_user.role in {UserRole.BUYER, UserRole.ADMIN}:
        closed = db.scalars(select(Auction).where(Auction.status == AuctionStatus.CLOSED)).all()
        won_count = sum(1 for auction in closed if (winner := highest_bid(db, auction.id)) is not None and winner.buyer_id == current_user.id)

    return templates.TemplateResponse(
        request=request, name="dashboard.html",
        context=template_context(request, current_user, seller_rows=seller_rows, buyer_bids=buyer_bids, available_auctions=available_auctions, won_count=won_count),
    )

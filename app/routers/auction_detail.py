from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload

from app.access import get_visible_auction
from app.auth import require_current_user
from app.db import get_db
from app.http import template_context, templates
from app.models import Auction, AuctionStatus, Bid, Lot, User, UserRole
from app.services import highest_bid, minimum_bid_for_auction, synchronize_auction_statuses

router = APIRouter()


@router.get("/auctions/{auction_id}", response_class=HTMLResponse, tags=["web"])
def auction_detail(
    auction_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    synchronize_auction_statuses(db)
    auction = get_visible_auction(db, current_user, auction_id)
    auction = db.query(Auction).options(joinedload(Auction.lot).joinedload(Lot.seller), joinedload(Auction.bids).joinedload(Bid.buyer)).filter(Auction.id == auction.id).one()
    bids = sorted(auction.bids, key=lambda bid: (Decimal(str(bid.amount)), -bid.id), reverse=True)
    winner = highest_bid(db, auction.id) if auction.status == AuctionStatus.CLOSED else None
    minimum_bid = minimum_bid_for_auction(db, auction)
    can_bid = current_user.role in {UserRole.BUYER, UserRole.ADMIN} and current_user.id != auction.lot.seller_id and auction.status == AuctionStatus.ACTIVE
    can_manage = current_user.id == auction.lot.seller_id or current_user.role == UserRole.ADMIN
    return templates.TemplateResponse(
        request=request, name="auction_detail.html",
        context=template_context(request, current_user, auction=auction, bids=bids, winner=winner, minimum_bid=minimum_bid, can_bid=can_bid, can_manage=can_manage),
    )

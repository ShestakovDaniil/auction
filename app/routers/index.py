import math
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_current_user
from app.config import get_settings
from app.db import get_db
from app.http import template_context, templates
from app.models import Auction, AuctionStatus, Bid, Lot, User, UserRole
from app.services import synchronize_auction_statuses

router = APIRouter()
settings = get_settings()


@router.get("/", response_class=HTMLResponse, tags=["web"])
def index(
    request: Request,
    page: int = Query(default=1, ge=1),
    q: str = Query(default="", max_length=100),
    status_filter: str = Query(default="active", alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    synchronize_auction_statuses(db)
    allowed_statuses = {"active", "pending", "closed", "all"}
    if status_filter not in allowed_statuses:
        status_filter = "active"

    query = db.query(Auction).join(Auction.lot).join(Lot.seller).options(joinedload(Auction.lot).joinedload(Lot.seller))
    clean_q = q.strip()
    if clean_q:
        pattern = f"%{clean_q}%"
        query = query.filter(or_(Lot.title.ilike(pattern), Lot.description.ilike(pattern), User.username.ilike(pattern)))
    if status_filter != "all":
        query = query.filter(Auction.status == AuctionStatus(status_filter))
    query = query.order_by(
        Auction.end_time.is_(None), Auction.end_time.asc(), Auction.id.desc()
    ) if status_filter == "active" else query.order_by(Auction.start_time.desc(), Auction.id.desc())

    total = query.count()
    page_size = max(1, min(settings.catalog_page_size, 30))
    total_pages = max(1, math.ceil(total / page_size))
    if page > total_pages:
        params = {"page": total_pages, "status": status_filter}
        if clean_q:
            params["q"] = clean_q
        return RedirectResponse(url=f"/?{urlencode(params)}", status_code=303)
    auctions = query.offset((page - 1) * page_size).limit(page_size).all()

    active_count = db.scalar(select(func.count(Auction.id)).where(Auction.status == AuctionStatus.ACTIVE)) or 0
    seller_count = db.scalar(select(func.count(User.id)).where(User.role.in_([UserRole.SELLER, UserRole.ADMIN]))) or 0
    bids_count = db.scalar(select(func.count(Bid.id))) or 0
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=template_context(
            request, current_user, auctions=auctions, q=clean_q, status_filter=status_filter,
            page=page, total=total, total_pages=total_pages, active_count=active_count,
            seller_count=seller_count, bids_count=bids_count,
        ),
    )

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import require_current_user
from app.db import get_db
from app.http import template_context, templates
from app.models import AuctionStatus, Lot, User, UserRole

router = APIRouter()


@router.get("/auctions/new", response_class=HTMLResponse, tags=["web"])
def new_auction_page(
    request: Request,
    lot_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    if current_user.role not in {UserRole.SELLER, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Создавать аукционы может только продавец")
    lots = db.query(Lot).options(joinedload(Lot.auctions)).filter(Lot.seller_id == current_user.id).order_by(Lot.created_at.desc()).all()
    eligible_lots = [lot for lot in lots if not any(a.status in {AuctionStatus.PENDING, AuctionStatus.ACTIVE} for a in lot.auctions)]
    selected_lot_id = lot_id if any(lot.id == lot_id for lot in eligible_lots) else None
    default_start = datetime.now().replace(second=0, microsecond=0)
    default_end = default_start + timedelta(days=1)
    return templates.TemplateResponse(
        request=request, name="auction_form.html",
        context=template_context(request, current_user, lots=eligible_lots, selected_lot_id=selected_lot_id,
            default_start=default_start.strftime("%Y-%m-%dT%H:%M"), default_end=default_end.strftime("%Y-%m-%dT%H:%M")),
    )

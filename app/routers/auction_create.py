from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.http import redirect_with_message
from app.models import User
from app.schemas import AuctionCreate
from app.security import verify_csrf
from app.services import create_auction

router = APIRouter()


@router.post("/auctions/create", tags=["web"])
def create_auction_web(
    request: Request,
    lot_id: int = Form(...),
    start_time: datetime = Form(...),
    end_time: datetime = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    verify_csrf(request, csrf_token)
    try:
        auction = create_auction(db, current_user, AuctionCreate(lot_id=lot_id, start_time=start_time, end_time=end_time))
    except (HTTPException, ValidationError) as exc:
        detail = str(exc.detail) if isinstance(exc, HTTPException) else "Проверьте даты и выбранный лот"
        return redirect_with_message(f"/auctions/new?lot_id={lot_id}", detail, "error")
    return redirect_with_message(f"/auctions/{auction.id}", "Аукцион создан и опубликован.")

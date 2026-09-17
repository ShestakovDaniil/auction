from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.http import redirect_with_message
from app.models import User
from app.schemas import BidCreate
from app.security import verify_csrf
from app.services import place_bid

router = APIRouter()


@router.post("/auctions/{auction_id}/bid", tags=["web"])
def place_bid_web(
    auction_id: int,
    request: Request,
    amount: Decimal = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    verify_csrf(request, csrf_token)
    try:
        place_bid(db, current_user, auction_id, BidCreate(amount=amount))
    except (HTTPException, ValidationError) as exc:
        detail = str(exc.detail) if isinstance(exc, HTTPException) else "Некорректная сумма ставки"
        return redirect_with_message(f"/auctions/{auction_id}", detail, "error")
    return redirect_with_message(f"/auctions/{auction_id}", "Ставка принята.")

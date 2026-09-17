from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.http import redirect_with_message
from app.models import User
from app.security import verify_csrf
from app.services import close_auction

router = APIRouter()


@router.post("/auctions/{auction_id}/close", tags=["web"])
def close_auction_web(
    auction_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    verify_csrf(request, csrf_token)
    try:
        close_auction(db, current_user, auction_id)
    except HTTPException as exc:
        return redirect_with_message(f"/auctions/{auction_id}", str(exc.detail), "error")
    return redirect_with_message(f"/auctions/{auction_id}", "Аукцион завершён.")

from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.http import redirect_with_message
from app.models import User
from app.schemas import LotCreate
from app.security import verify_csrf
from app.services import create_lot

router = APIRouter()


@router.post("/lots/create", tags=["web"])
def create_lot_web(
    request: Request,
    title: str = Form(...),
    description: str = Form(default=""),
    start_price: Decimal = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    verify_csrf(request, csrf_token)
    try:
        lot = create_lot(db, current_user, LotCreate(title=title, description=description, start_price=start_price))
    except (HTTPException, ValidationError) as exc:
        detail = str(exc.detail) if isinstance(exc, HTTPException) else "Проверьте данные лота"
        return redirect_with_message("/lots/new", detail, "error")
    return redirect_with_message(f"/auctions/new?lot_id={lot.id}", "Лот сохранён. Теперь настройте аукцион.")

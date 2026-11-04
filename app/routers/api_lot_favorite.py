from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.models import User
from app.security import require_api_csrf
from app.services import add_favorite, remove_favorite

router = APIRouter(prefix="/api/lots", tags=["api: favorites"])


@router.put("/{lot_id}/favorite", dependencies=[Depends(require_api_csrf)])
def save_favorite(lot_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    item = add_favorite(db, user, lot_id)
    return {"lot_id": item.lot_id, "saved": True}


@router.delete("/{lot_id}/favorite", status_code=204, dependencies=[Depends(require_api_csrf)])
def unsave_favorite(lot_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    remove_favorite(db, user, lot_id)
    return Response(status_code=204)

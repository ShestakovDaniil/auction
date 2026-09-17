from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.access import get_visible_lot
from app.auth import require_current_user
from app.db import get_db
from app.models import User
from app.schemas import LotRead

router = APIRouter(prefix="/api/lots", tags=["api: lots"])


@router.get("/{lot_id}", response_model=LotRead)
def get_lot(lot_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_current_user)):
    return get_visible_lot(db, current_user, lot_id)

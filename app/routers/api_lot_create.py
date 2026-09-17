from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.models import User
from app.schemas import LotCreate, LotRead
from app.security import require_api_csrf
from app.services import create_lot

router = APIRouter(prefix="/api/lots", tags=["api: lots"])


@router.post("", response_model=LotRead, status_code=201, dependencies=[Depends(require_api_csrf)])
def add_lot(payload: LotCreate, db: Session = Depends(get_db), current_user: User = Depends(require_current_user)):
    return create_lot(db, current_user, payload)

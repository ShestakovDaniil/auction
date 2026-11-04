from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.models import User
from app.schemas import LotRead
from app.services import list_favorites

router = APIRouter(prefix="/api/users", tags=["api: favorites"])


@router.get("/me/favorites", response_model=list[LotRead])
def my_favorites(db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    return list_favorites(db, user)

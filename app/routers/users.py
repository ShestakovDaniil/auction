from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_current_user
from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserRead
from app.services import create_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(require_current_user)):
    return current_user


@router.post("", response_model=UserRead, status_code=201)
def add_user(payload: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, payload)

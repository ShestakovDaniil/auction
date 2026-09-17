from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserRead
from app.services import create_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("", response_model=UserRead, status_code=201)
def add_user(payload: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, payload)

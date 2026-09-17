from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import UserCreate, UserRead
from app.services import create_user

router = APIRouter(prefix="/api/users", tags=["api: users"])


@router.post("", response_model=UserRead, status_code=201)
def add_user(payload: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, payload)

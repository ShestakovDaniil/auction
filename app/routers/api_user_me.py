from fastapi import APIRouter, Depends

from app.auth import require_current_user
from app.models import User
from app.schemas import UserRead

router = APIRouter(prefix="/api/users", tags=["api: users"])


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(require_current_user)):
    return current_user

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.auth import require_current_user
from app.http import template_context, templates
from app.models import User, UserRole

router = APIRouter()


@router.get("/lots/new", response_class=HTMLResponse, tags=["web"])
def new_lot_page(request: Request, current_user: User = Depends(require_current_user)):
    if current_user.role not in {UserRole.SELLER, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Создавать лоты может только продавец")
    return templates.TemplateResponse(request=request, name="lot_form.html", context=template_context(request, current_user))

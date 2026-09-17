from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import get_current_user_from_cookie
from app.db import get_db
from app.http import redirect_with_message, template_context, templates
from app.models import User, UserRole
from app.schemas import UserCreate
from app.security import verify_csrf
from app.services import create_user

router = APIRouter()


@router.get("/register", response_class=HTMLResponse, tags=["web"])
def register_page(request: Request, current_user: User | None = Depends(get_current_user_from_cookie)):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="register.html", context=template_context(request))


@router.post("/register", response_class=HTMLResponse, tags=["web"])
def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    form_data = {"username": username.strip(), "email": email.strip(), "role": role}
    try:
        payload = UserCreate(username=username, email=email, password=password, role=UserRole(role))
        create_user(db, payload)
    except (ValidationError, ValueError) as exc:
        error = "Проверьте корректность логина, email, пароля и роли"
        if isinstance(exc, ValueError) and not isinstance(exc, ValidationError):
            error = "Некорректная роль"
        return templates.TemplateResponse(
            request=request, name="register.html", status_code=400,
            context=template_context(request, error=error, form_data=form_data),
        )
    except HTTPException as exc:
        return templates.TemplateResponse(
            request=request, name="register.html", status_code=exc.status_code,
            context=template_context(request, error=str(exc.detail), form_data=form_data),
        )
    return redirect_with_message("/login", "Аккаунт создан. Теперь войдите в систему.")

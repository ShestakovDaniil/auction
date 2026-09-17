from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user_from_cookie, hash_password, password_needs_upgrade, verify_password
from app.config import get_settings
from app.db import get_db
from app.http import template_context, templates
from app.models import User
from app.security import client_key, login_rate_limiter, safe_local_url, verify_csrf

router = APIRouter()
settings = get_settings()
_DUMMY_HASH = hash_password("dummy-password-only-for-timing")


@router.get("/login", response_class=HTMLResponse, tags=["web"])
def login_page(
    request: Request,
    next: str = "/dashboard",
    current_user: User | None = Depends(get_current_user_from_cookie),
):
    next_url = safe_local_url(next)
    if current_user:
        return RedirectResponse(url=next_url, status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context=template_context(request, next_url=next_url))


@router.post("/login", response_class=HTMLResponse, tags=["web"])
def login_user(
    request: Request,
    identity: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/dashboard"),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    clean_identity = identity.strip()[:100]
    if len(password) > 128:
        password = ""
    key = client_key(request, clean_identity)
    login_rate_limiter.ensure_allowed(key)
    user = db.scalar(select(User).where(or_(User.username == clean_identity, User.email == clean_identity.lower())))
    stored_hash = user.hashed_password if user else _DUMMY_HASH
    password_ok = verify_password(password, stored_hash)
    if not user or not password_ok:
        login_rate_limiter.register_failure(key)
        return templates.TemplateResponse(
            request=request, name="login.html", status_code=400,
            context=template_context(request, error="Неверный логин/email или пароль", identity=clean_identity, next_url=safe_local_url(next)),
        )
    login_rate_limiter.clear(key)
    if password_needs_upgrade(user.hashed_password):
        user.hashed_password = hash_password(password)
        db.commit()

    response = RedirectResponse(url=safe_local_url(next), status_code=303)
    response.set_cookie(
        key="access_token", value=create_access_token(user), httponly=True,
        secure=settings.cookie_secure, samesite="strict",
        max_age=settings.access_token_expire_minutes * 60, path="/",
    )
    return response

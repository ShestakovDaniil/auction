from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.models import User
from app.security import csrf_token_for_request

settings = get_settings()
templates = Jinja2Templates(directory="app/templates")


def format_money(value) -> str:
    if value is None:
        return "0,00"
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    return f"{amount:,.2f}".replace(",", " ").replace(".", ",")


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "Без срока"
    return value.strftime("%d.%m.%Y %H:%M")


templates.env.filters["money"] = format_money
templates.env.filters["dt"] = format_datetime


def template_context(request: Request, current_user: User | None = None, **extra):
    return {
        "request": request,
        "current_user": current_user,
        "message": request.query_params.get("message"),
        "message_level": request.query_params.get("level", "info"),
        "app_name": settings.app_name,
        "csrf_token": csrf_token_for_request(request),
        **extra,
    }


def redirect_with_message(url: str, message: str, level: str = "success") -> RedirectResponse:
    separator = "&" if "?" in url else "?"
    return RedirectResponse(
        url=f"{url}{separator}{urlencode({'message': message, 'level': level})}",
        status_code=303,
    )

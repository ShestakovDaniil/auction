from __future__ import annotations

from contextlib import asynccontextmanager
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.auth import decode_user_id
from app.config import get_settings
from app.db import Base, get_engine
from app.http import template_context, templates
from app.routers import ALL_ROUTERS
from app.security import CSRF_COOKIE_NAME

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=get_engine())
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
for router in ALL_ROUTERS:
    app.include_router(router)


def _is_public_request(request: Request) -> bool:
    path = request.url.path
    if path.startswith("/static/"):
        return True
    if path in {"/login", "/register", "/health", "/redoc", "/openapi.json"} or path.startswith("/docs"):
        return True
    if path == "/api/users" and request.method == "POST":
        return True
    return False


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 1_048_576:
                return JSONResponse(status_code=413, content={"detail": "Тело запроса слишком большое"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Некорректный Content-Length"})

    if not _is_public_request(request):
        token = request.cookies.get("access_token")
        if not token or decode_user_id(token) is None:
            if request.url.path.startswith("/api/"):
                return JSONResponse(status_code=401, content={"detail": "Необходимо войти в систему"})
            next_url = request.url.path
            if request.url.query:
                next_url += f"?{request.url.query}"
            return RedirectResponse(url=f"/login?{urlencode({'next': next_url})}", status_code=303)

    response = await call_next(request)

    new_csrf = getattr(request.state, "new_csrf_token", None)
    if new_csrf:
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=new_csrf,
            httponly=False,
            secure=settings.cookie_secure,
            samesite="strict",
            max_age=settings.access_token_expire_minutes * 60,
            path="/",
        )

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith("/docs") or request.url.path == "/redoc":
        csp = (
            "default-src 'self'; img-src 'self' data: https://fastapi.tiangolo.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'"
        )
    else:
        csp = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
    response.headers.setdefault("Content-Security-Policy", csp)
    if settings.cookie_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.cookies.get("access_token") or request.url.path in {"/login", "/register", "/dashboard"}:
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(HTTPException)
async def pretty_http_error(request: Request, exc: HTTPException):
    accepts_html = "text/html" in request.headers.get("accept", "")
    if exc.status_code == 401 and accepts_html and not request.url.path.startswith("/api/"):
        return RedirectResponse(url=f"/login?{urlencode({'next': request.url.path})}", status_code=303)
    if accepts_html and not request.url.path.startswith("/api/"):
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            status_code=exc.status_code,
            context=template_context(request, error_code=exc.status_code, error_message=str(exc.detail)),
        )
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def pretty_validation_error(request: Request, exc: RequestValidationError):
    accepts_html = "text/html" in request.headers.get("accept", "")
    if accepts_html and not request.url.path.startswith("/api/"):
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            status_code=422,
            context=template_context(request, error_code=422, error_message="Проверьте заполнение формы: одно или несколько значений имеют неверный формат."),
        )
    return await request_validation_exception_handler(request, exc)

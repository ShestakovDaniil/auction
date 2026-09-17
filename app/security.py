from __future__ import annotations

import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlsplit

from fastapi import Header, HTTPException, Request, status

from app.config import get_settings

settings = get_settings()

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
CSRF_COOKIE_NAME = "csrf_token"


class LoginRateLimiter:
    """Small in-memory limiter for repeated failed logins.

    It is intentionally process-local: it protects a single application instance
    without introducing another infrastructure dependency.
    """

    def __init__(self, max_attempts: int = 8, window_seconds: int = 300) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        attempts = self._attempts[key]
        threshold = now - self.window_seconds
        while attempts and attempts[0] < threshold:
            attempts.popleft()
        return attempts

    def ensure_allowed(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            attempts = self._prune(key, now)
            if len(attempts) >= self.max_attempts:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Слишком много неудачных попыток входа. Повторите позже.",
                )

    def register_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            attempts = self._prune(key, now)
            attempts.append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)


login_rate_limiter = LoginRateLimiter()


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_token_for_request(request: Request) -> str:
    token = request.cookies.get(CSRF_COOKIE_NAME)
    if token and len(token) >= 32:
        return token
    token = getattr(request.state, "new_csrf_token", None)
    if not token:
        token = new_csrf_token()
        request.state.new_csrf_token = token
    return token


def verify_csrf(request: Request, supplied_token: str | None) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie_token or not supplied_token:
        raise HTTPException(status_code=403, detail="Некорректный CSRF-токен")
    if not hmac.compare_digest(cookie_token, supplied_token):
        raise HTTPException(status_code=403, detail="Некорректный CSRF-токен")


def require_api_csrf(
    request: Request,
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    verify_csrf(request, x_csrf_token)


def safe_local_url(value: str | None, default: str = "/dashboard") -> str:
    if not value:
        return default
    if any(ch in value for ch in ("\r", "\n", "\\")):
        return default
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/") or parsed.path.startswith("//"):
        return default
    return value


def client_key(request: Request, identity: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{identity.strip().lower()[:100]}"

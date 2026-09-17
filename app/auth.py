from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User, UserRole

settings = get_settings()
PBKDF2_ITERATIONS = 310_000
access_token_cookie = APIKeyCookie(name="access_token", auto_error=False)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def hash_password(password: str) -> str:
    if len(password) < 8 or len(password) > 128:
        raise ValueError("Пароль должен содержать от 8 до 128 символов")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def _is_legacy_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def verify_password(plain_password: str, stored_password: str) -> bool:
    if _is_legacy_sha256(stored_password):
        legacy = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy, stored_password)
    try:
        scheme, iterations_raw, salt_raw, digest_raw = stored_password.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        if iterations < 100_000 or iterations > 2_000_000:
            return False
        salt = base64.urlsafe_b64decode(salt_raw.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_raw.encode("ascii"))
    except (ValueError, TypeError, base64.binascii.Error):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def password_needs_upgrade(stored_password: str) -> bool:
    if _is_legacy_sha256(stored_password):
        return True
    try:
        scheme, iterations_raw, *_ = stored_password.split("$", 3)
        return scheme != "pbkdf2_sha256" or int(iterations_raw) < PBKDF2_ITERATIONS
    except (ValueError, TypeError):
        return True


def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    expires_in = int((expires_delta or timedelta(minutes=settings.access_token_expire_minutes)).total_seconds())
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": str(user.id), "iat": now, "exp": now + expires_in}
    header_part = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(settings.app_secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_part}.{payload_part}.{_b64url_encode(signature)}"


def decode_user_id(token: str) -> int | None:
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        expected_signature = hmac.new(settings.app_secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_signature = _b64url_decode(signature_part)
        if not hmac.compare_digest(actual_signature, expected_signature):
            return None
        header = json.loads(_b64url_decode(header_part))
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            return None
        payload = json.loads(_b64url_decode(payload_part))
        now = int(time.time())
        if int(payload.get("exp", 0)) <= now or int(payload.get("iat", now + 1)) > now + 60:
            return None
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.isdigit():
            return None
        user_id = int(subject)
        return user_id if user_id > 0 else None
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError, base64.binascii.Error):
        return None


def get_current_user_from_cookie(
    token: str | None = Security(access_token_cookie),
    db: Session = Depends(get_db),
) -> User | None:
    if not token:
        return None
    user_id = decode_user_id(token)
    if user_id is None:
        return None
    return db.get(User, user_id)


def require_current_user(user: User | None = Security(get_current_user_from_cookie)) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Необходимо войти в систему")
    return user


def require_roles(*roles: UserRole):
    def dependency(user: User = Security(require_current_user)) -> User:
        if user.role not in set(roles):
            raise HTTPException(status_code=403, detail="Недостаточно прав для выполнения операции")
        return user
    return dependency

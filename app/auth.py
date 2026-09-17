import base64
import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

settings = get_settings()
PBKDF2_ITERATIONS = 310_000


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def hash_password(password: str) -> str:
    if len(password) < 6:
        raise ValueError("Пароль должен содержать минимум 6 символов")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
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
        salt = base64.urlsafe_b64decode(salt_raw.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_raw.encode("ascii"))
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual, expected)


def password_needs_upgrade(stored_password: str) -> bool:
    return _is_legacy_sha256(stored_password)


def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    expires_in = int(
        (expires_delta or timedelta(minutes=settings.access_token_expire_minutes)).total_seconds()
    )
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        # JWT subject is deliberately a string. This fixes the old 401 bug.
        "sub": str(user.id),
        "role": user.role.value,
        "username": user.username,
        "exp": int(time.time()) + expires_in,
    }
    header_part = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(
        settings.app_secret_key.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    return f"{header_part}.{payload_part}.{_b64url_encode(signature)}"


def decode_user_id(token: str) -> int | None:
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        expected_signature = hmac.new(
            settings.app_secret_key.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        actual_signature = _b64url_decode(signature_part)
        if not hmac.compare_digest(actual_signature, expected_signature):
            return None

        header = json.loads(_b64url_decode(header_part))
        if header.get("alg") != "HS256":
            return None
        payload = json.loads(_b64url_decode(payload_part))
        if int(payload.get("exp", 0)) <= int(time.time()):
            return None
        subject = payload.get("sub")
        if not isinstance(subject, str):
            return None
        return int(subject)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def get_current_user_from_cookie(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token[7:]
    user_id = decode_user_id(token)
    if user_id is None:
        return None
    return db.get(User, user_id)


def require_current_user(
    user: Optional[User] = Depends(get_current_user_from_cookie),
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Необходимо войти в систему",
        )
    return user

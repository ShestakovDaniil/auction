import hashlib

from app.auth import create_access_token, decode_user_id, hash_password, password_needs_upgrade, verify_password
from app.models import User, UserRole


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("secret123")
    second = hash_password("secret123")
    assert first != second
    assert verify_password("secret123", first)
    assert not verify_password("wrong", first)


def test_legacy_sha256_password_is_still_supported():
    legacy = hashlib.sha256(b"old-password").hexdigest()
    assert password_needs_upgrade(legacy)
    assert verify_password("old-password", legacy)
    assert not verify_password("wrong-password", legacy)


def test_jwt_subject_round_trip_is_integer_user_id():
    user = User(id=42, username="tester", email="tester@example.com", hashed_password="x", role=UserRole.BUYER)
    token = create_access_token(user)
    assert decode_user_id(token) == 42

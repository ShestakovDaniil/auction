from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import Settings
from app.models import UserRole
from app.schemas import AuctionCreate, BidCreate, LotCreate, UserCreate
from app.security import LoginRateLimiter, safe_local_url
from app.services import _validate_auction_window, as_money


@pytest.mark.parametrize("username", ["   ", " x ", "a\nb", "a\x00b"])
def test_rejects_bad_username(username):
    with pytest.raises(ValidationError):
        UserCreate(username=username, email="a@example.org", password="12345678")


def test_user_role_and_password_validation():
    with pytest.raises(ValidationError):
        UserCreate(username="user", email="not-an-email", password="12345678")
    with pytest.raises(ValidationError):
        UserCreate(username="user", email="a@example.org", password="short")
    assert UserCreate(username=" user ", email="a@example.org", password="12345678", role=UserRole.BUYER).username == "user"


@pytest.mark.parametrize("title,price", [(" ", "1"), ("valid", "0"), ("valid", "-1"), ("valid", "1.001")])
def test_invalid_lots(title, price):
    with pytest.raises(ValidationError):
        LotCreate(title=title, start_price=Decimal(price))


@pytest.mark.parametrize("amount", ["0", "-1", "1.001", "1000000000000"])
def test_invalid_bids(amount):
    with pytest.raises(ValidationError):
        BidCreate(amount=Decimal(amount))


def test_money_rounding():
    assert as_money("1.235") == Decimal("1.24")
    assert as_money("2") == Decimal("2.00")


def test_auction_time_validation():
    now = datetime.now()
    with pytest.raises(HTTPException) as err:
        _validate_auction_window(now, now)
    assert err.value.status_code == 422
    assert AuctionCreate(lot_id=1, start_time=now, end_time=now + timedelta(seconds=1))


@pytest.mark.parametrize("url", ["https://evil.org/x", "//evil.org/x", "\\evil", "/\r\nevil", "abc", "javascript:alert(1)"])
def test_open_redirect_rejected(url):
    assert safe_local_url(url) == "/dashboard"


def test_safe_redirect():
    assert safe_local_url("/lots?page=1") == "/lots?page=1"


def test_login_rate_limit():
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=300)
    limiter.register_failure("ip:user")
    limiter.ensure_allowed("ip:user")
    limiter.register_failure("ip:user")
    with pytest.raises(HTTPException) as err:
        limiter.ensure_allowed("ip:user")
    assert err.value.status_code == 429
    limiter.clear("ip:user")
    limiter.ensure_allowed("ip:user")


def test_increment_settings_must_represent_real_money():
    base = {
        "database_url": "mysql+pymysql://user:pass@localhost/auction_test",
        "app_secret_key": "a" * 48,
    }
    for bad_increment in ("0", "-1", "0.001"):
        with pytest.raises(ValidationError):
            Settings(**base, min_bid_increment=bad_increment)
    assert Settings(**base, min_bid_increment="0.01").min_bid_increment == Decimal("0.01")

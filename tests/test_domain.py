from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.domain import DomainRuleError, minimum_allowed_bid, validate_bid_amount, validate_bid_window


def test_first_bid_uses_start_price():
    assert minimum_allowed_bid(Decimal("100.00"), Decimal("10.00"), None) == Decimal("100.00")


def test_next_bid_requires_increment():
    assert minimum_allowed_bid(Decimal("100.00"), Decimal("10.00"), Decimal("140.00")) == Decimal("150.00")


def test_low_bid_is_rejected():
    with pytest.raises(DomainRuleError):
        validate_bid_amount(Decimal("149.99"), Decimal("150.00"))


def test_bid_outside_auction_window_is_rejected():
    now = datetime.now()
    with pytest.raises(DomainRuleError):
        validate_bid_window(now, now + timedelta(minutes=1), now + timedelta(hours=1))

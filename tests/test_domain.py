from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.domain import DomainRuleError, minimum_allowed_bid, validate_bid_amount, validate_bid_window


@pytest.mark.parametrize("start,increment,current,expected", [
    ("10.00", "1.00", None, "10.00"),
    ("10.00", "1.00", "10.00", "11.00"),
    ("100.00", "0.01", "109.99", "110.00"),
    ("10.00", "5.00", "99.00", "104.00"),
])
def test_bid_minimum(start, increment, current, expected):
    result = minimum_allowed_bid(Decimal(start), Decimal(increment), Decimal(current) if current is not None else None)
    assert result == Decimal(expected)


@pytest.mark.parametrize("amount,minimum", [("10", "10"), ("11", "10"), ("0.01", "0.01")])
def test_valid_amount(amount, minimum):
    validate_bid_amount(Decimal(amount), Decimal(minimum))


@pytest.mark.parametrize("amount,minimum", [("9.99", "10"), ("0", "0.01"), ("-1", "10")])
def test_below_minimum(amount, minimum):
    with pytest.raises(DomainRuleError, match="Bid must be at least"):
        validate_bid_amount(Decimal(amount), Decimal(minimum))


def test_start_boundary_inclusive_and_end_exclusive():
    start = datetime(2026, 1, 1, 12)
    end = start + timedelta(hours=1)
    validate_bid_window(start, start, end)
    validate_bid_window(end - timedelta(microseconds=1), start, end)
    with pytest.raises(DomainRuleError, match="not started"):
        validate_bid_window(start - timedelta(microseconds=1), start, end)
    with pytest.raises(DomainRuleError, match="already ended"):
        validate_bid_window(end, start, end)

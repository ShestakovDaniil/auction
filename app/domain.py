from datetime import datetime
from decimal import Decimal


class DomainRuleError(ValueError):
    """Raised when a business rule of the auction domain is violated."""


def minimum_allowed_bid(
    start_price: Decimal,
    min_increment: Decimal,
    current_highest: Decimal | None,
) -> Decimal:
    if current_highest is None:
        return start_price
    return current_highest + min_increment


def validate_bid_window(now: datetime, starts_at: datetime, ends_at: datetime) -> None:
    if now < starts_at:
        raise DomainRuleError("Auction has not started yet")
    if now >= ends_at:
        raise DomainRuleError("Auction has already ended")


def validate_bid_amount(amount: Decimal, minimum: Decimal) -> None:
    if amount < minimum:
        raise DomainRuleError(f"Bid must be at least {minimum:.2f}")

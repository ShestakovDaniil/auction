from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import AuctionStatus, Bid, FavoriteLot, LotStatus, UserRole
from app.schemas import AuctionCreate, BidCreate, LotCreate, UserCreate
from app.services import (
    add_favorite, close_auction, create_auction, create_lot, create_user, highest_bid,
    list_favorites, minimum_bid_for_auction, place_bid, remove_favorite, synchronize_auction_statuses,
)


def assert_http(code, fn, *args):
    with pytest.raises(HTTPException) as exc:
        fn(*args)
    assert exc.value.status_code == code


def lot_for(db, user, price="100"):
    return create_lot(db, user, LotCreate(title="Rare coin", start_price=price, description="Collectable"))


def auction_for(db, seller, lot, *, start_offset=-60, end_offset=3600):
    now = datetime.now()
    return create_auction(db, seller, AuctionCreate(
        lot_id=lot.id, start_time=now + timedelta(seconds=start_offset), end_time=now + timedelta(seconds=end_offset)
    ))


def test_public_registration_rejects_admin_and_duplicate(db):
    assert_http(403, create_user, db, UserCreate(username="superuser", email="root@example.org", password="strong-password", role=UserRole.ADMIN))
    user = create_user(db, UserCreate(username="abc", email="AbC@example.org", password="strong-password"))
    assert user.email == "abc@example.org"
    assert user.hashed_password != "strong-password"
    assert_http(409, create_user, db, UserCreate(username="abc", email="another@example.org", password="strong-password"))
    assert_http(409, create_user, db, UserCreate(username="xyz", email="abc@example.org", password="strong-password"))


def test_lot_role_and_initial_status(db, actors):
    seller, buyer, _, admin = actors
    assert_http(403, create_lot, db, buyer, LotCreate(title="Object", start_price="2"))
    lot = lot_for(db, seller)
    assert lot.status == LotStatus.DRAFT
    assert lot.start_price == Decimal("100.00")
    assert create_lot(db, admin, LotCreate(title="Admin item", start_price="3")).seller_id == admin.id


def test_auction_ownership_window_and_duplicate(db, actors):
    seller, buyer, other, admin = actors
    lot = lot_for(db, seller)
    now = datetime.now()
    data = AuctionCreate(lot_id=lot.id, start_time=now, end_time=now + timedelta(hours=2))
    assert_http(403, create_auction, db, buyer, data)
    assert_http(404, create_auction, db, other, data)
    assert_http(422, create_auction, db, seller, AuctionCreate(lot_id=lot.id, start_time=now, end_time=now))
    assert_http(422, create_auction, db, seller, AuctionCreate(lot_id=lot.id, start_time=now - timedelta(days=2), end_time=now - timedelta(days=1)))
    auction = create_auction(db, seller, data)
    assert auction.status == AuctionStatus.ACTIVE
    assert lot.status == LotStatus.ACTIVE
    assert_http(409, create_auction, db, seller, data)
    # Admin can launch an auction for another seller's lot.
    lot2 = lot_for(db, seller)
    assert create_auction(db, admin, AuctionCreate(lot_id=lot2.id, start_time=now, end_time=now + timedelta(hours=1)))


def test_bids_step_first_bid_tie_order_and_close(db, actors):
    seller, buyer, _, admin = actors
    auction = auction_for(db, seller, lot_for(db, seller))
    assert minimum_bid_for_auction(db, auction) == Decimal("100.00")
    assert_http(403, place_bid, db, seller, auction.id, BidCreate(amount="100"))
    assert_http(422, place_bid, db, buyer, auction.id, BidCreate(amount="99.99"))
    first = place_bid(db, buyer, auction.id, BidCreate(amount="100"))
    assert first.amount == Decimal("100.00")
    assert minimum_bid_for_auction(db, auction) == Decimal("101.00")
    assert_http(422, place_bid, db, buyer, auction.id, BidCreate(amount="100.99"))
    second = place_bid(db, buyer, auction.id, BidCreate(amount="101"))
    assert highest_bid(db, auction.id).id == second.id
    assert_http(404, close_auction, db, buyer, auction.id)
    closed = close_auction(db, seller, auction.id)
    assert closed.status == AuctionStatus.CLOSED
    assert closed.lot.status == LotStatus.CLOSED
    assert_http(409, place_bid, db, buyer, auction.id, BidCreate(amount="200"))
    assert_http(409, close_auction, db, admin, auction.id)


def test_no_bids_pending_expired_and_missing(db, actors):
    seller, buyer, _, admin = actors
    assert_http(404, close_auction, db, admin, 999)
    assert_http(404, place_bid, db, buyer, 999, BidCreate(amount="1"))
    lot = lot_for(db, seller)
    auction = auction_for(db, seller, lot, start_offset=3600, end_offset=7200)
    assert auction.status == AuctionStatus.PENDING
    assert_http(409, place_bid, db, buyer, auction.id, BidCreate(amount="100"))
    auction.start_time = datetime.now() - timedelta(seconds=5)
    db.commit()
    assert synchronize_auction_statuses(db) == 1
    assert auction.status == AuctionStatus.ACTIVE
    auction.end_time = datetime.now() - timedelta(seconds=1)
    db.commit()
    assert synchronize_auction_statuses(db) == 1
    assert auction.status == AuctionStatus.CLOSED
    assert lot.status == LotStatus.CLOSED


def test_favorites_unique_visibility_remove(db, actors):
    seller, buyer, other, admin = actors
    lot = lot_for(db, seller)
    assert_http(404, add_favorite, db, buyer, lot.id)  # private draft
    assert add_favorite(db, seller, lot.id).lot_id == lot.id
    assert len(list_favorites(db, seller)) == 1
    auction_for(db, seller, lot)
    assert add_favorite(db, buyer, lot.id).lot_id == lot.id
    assert add_favorite(db, buyer, lot.id).lot_id == lot.id  # idempotent
    assert db.scalar(select(func.count(FavoriteLot.id)).where(FavoriteLot.user_id == buyer.id)) == 1
    assert list_favorites(db, buyer)[0].id == lot.id
    assert list_favorites(db, other) == []
    assert list_favorites(db, admin) == []
    remove_favorite(db, buyer, lot.id)
    remove_favorite(db, buyer, lot.id)
    assert list_favorites(db, buyer) == []


def test_favorite_unique_constraint_at_database_level(db, actors):
    seller, buyer, _, _ = actors
    lot = lot_for(db, seller)
    db.add_all([FavoriteLot(user_id=buyer.id, lot_id=lot.id), FavoriteLot(user_id=buyer.id, lot_id=lot.id)])
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_highest_bid_tie_breaks_by_timestamp_then_id(db, actors):
    seller, buyer, _, admin = actors
    auction = auction_for(db, seller, lot_for(db, seller))
    moment = datetime.now()
    db.add_all([
        Bid(auction_id=auction.id, buyer_id=buyer.id, amount="100", created_at=moment),
        Bid(auction_id=auction.id, buyer_id=admin.id, amount="100", created_at=moment - timedelta(seconds=1)),
        Bid(auction_id=auction.id, buyer_id=buyer.id, amount="99", created_at=moment),
    ])
    db.commit()
    assert highest_bid(db, auction.id).buyer_id == admin.id

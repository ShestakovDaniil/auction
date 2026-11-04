"""Real MariaDB tests: test DB must be disposable and end with '_test'."""
import os
from pathlib import Path

from dotenv import dotenv_values

from alembic import command
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine.url import make_url

from scripts.db_backup import backup_database, restore_database
from scripts.migrate import alembic_config, migrate_database

pytestmark = pytest.mark.mariadb


@pytest.fixture
def mariadb_url():
    url = os.getenv("TEST_DATABASE_URL") or dotenv_values(".env").get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("TEST_DATABASE_URL обязателен для make verify; используйте отдельную *_test БД")
    parsed = make_url(url)
    if parsed.drivername not in {"mysql+pymysql", "mariadb+pymysql"} or not (parsed.database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL должен указывать на MariaDB/MySQL базу с суффиксом _test")
    prod_url = os.environ.get("AUCTION_PROD_DATABASE_URL")
    if prod_url:
        prod = make_url(prod_url)
        if (prod.host, prod.port, prod.database) == (parsed.host, parsed.port, parsed.database):
            pytest.fail("Нельзя запускать тесты на рабочей базе данных")
    return url


def reset_test_db(url):
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            for table in inspect(conn).get_table_names():
                conn.execute(text(f"DROP TABLE {engine.dialect.identifier_preparer.quote(table)}"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    finally:
        engine.dispose()


@pytest.fixture
def empty_test_db(mariadb_url):
    reset_test_db(mariadb_url)
    yield mariadb_url
    reset_test_db(mariadb_url)


def test_mariadb_fresh_migration_and_integrity(empty_test_db):
    url = empty_test_db
    migrate_database(url)
    engine = create_engine(url)
    try:
        assert "favorite_lots" in inspect(engine).get_table_names()
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users (username, email, hashed_password, role, created_at) VALUES ('a', 'a@example.org', 'hash', 'SELLER', NOW())"))
            conn.execute(text("INSERT INTO lots (title, start_price, seller_id, status, created_at) VALUES ('old coin', 100, 1, 'DRAFT', NOW())"))
            assert conn.scalar(text("SELECT `condition` FROM lots LIMIT 1")) == "used"
    finally:
        engine.dispose()


def test_mariadb_legacy_upgrade_and_restore(empty_test_db, tmp_path: Path):
    url = empty_test_db
    command.upgrade(alembic_config(url), "0001")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (id, username, email, hashed_password, role, created_at) VALUES (1,'legacy','legacy@example.org','hash','SELLER',NOW())"))
        conn.execute(text("INSERT INTO lots (id, title, start_price, seller_id, status, created_at) VALUES (1,'original',100,1,'DRAFT',NOW())"))
        conn.execute(text("DROP TABLE alembic_version"))
    engine.dispose()

    migrate_database(url)
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT title FROM lots WHERE id=1")) == "original"
        assert conn.scalar(text("SELECT `condition` FROM lots WHERE id=1")) == "used"
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
    engine.dispose()

    backup_file = backup_database(url, tmp_path / "before-corruption.sql.gz")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("UPDATE lots SET title='CORRUPTED' WHERE id=1"))
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT title FROM lots WHERE id=1")) == "CORRUPTED"
    engine.dispose()

    restore_database(url, backup_file, make_url(url).database)
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT title FROM lots WHERE id=1")) == "original"
            assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
    finally:
        engine.dispose()


def test_restore_requires_name_confirmation(empty_test_db, tmp_path: Path):
    from scripts.db_backup import restore_database
    with pytest.raises(ValueError, match="CONFIRM_RESTORE"):
        restore_database(empty_test_db, tmp_path / "fake.sql.gz", "wrong")


def test_mariadb_real_business_operations(empty_test_db):
    """Execute the main user→lot→auction→bid flow against actual InnoDB rows."""
    from datetime import datetime, timedelta
    from decimal import Decimal

    from fastapi import HTTPException
    from sqlalchemy.orm import Session

    from app.models import User, UserRole
    from app.schemas import AuctionCreate, BidCreate, LotCreate
    from app.services import add_favorite, close_auction, create_auction, create_lot, highest_bid, place_bid

    migrate_database(empty_test_db)
    engine = create_engine(empty_test_db)
    try:
        with Session(engine, expire_on_commit=False) as db:
            seller = User(username="seller", email="s@example.org", hashed_password="fake-hash", role=UserRole.SELLER)
            buyer = User(username="buyer", email="b@example.org", hashed_password="fake-hash", role=UserRole.BUYER)
            db.add_all([seller, buyer])
            db.commit()
            lot = create_lot(db, seller, LotCreate(title="InnoDB auction", start_price=Decimal("100.00")))
            auction = create_auction(db, seller, AuctionCreate(
                lot_id=lot.id, start_time=datetime.now() - timedelta(minutes=1),
                end_time=datetime.now() + timedelta(hours=1)
            ))
            bid1 = place_bid(db, buyer, auction.id, BidCreate(amount=Decimal("100.00")))
            assert bid1.amount == Decimal("100.00")
            with pytest.raises(HTTPException) as below_min:
                place_bid(db, buyer, auction.id, BidCreate(amount=Decimal("100.99")))
            assert below_min.value.status_code == 422
            bid2 = place_bid(db, buyer, auction.id, BidCreate(amount=Decimal("101.00")))
            assert highest_bid(db, auction.id).id == bid2.id
            favorite = add_favorite(db, buyer, lot.id)
            assert add_favorite(db, buyer, lot.id).id == favorite.id
            close_auction(db, seller, auction.id)
            with pytest.raises(HTTPException) as closed:
                place_bid(db, buyer, auction.id, BidCreate(amount=Decimal("200.00")))
            assert closed.value.status_code == 409
    finally:
        engine.dispose()

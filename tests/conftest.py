"""Isolated test settings; never open the application's production database."""
import os

from dotenv import dotenv_values
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# Preserve the actual application's URL only for safety comparison; never connect to it.
os.environ["AUCTION_PROD_DATABASE_URL"] = (
    os.environ.get("DATABASE_URL") or dotenv_values(".env").get("DATABASE_URL") or ""
)
os.environ["APP_ENV"] = "test"
os.environ["APP_SECRET_KEY"] = "test-only-very-long-unpredictable-key-not-a-production-secret"
os.environ["DATABASE_URL"] = "mysql+pymysql://example:example@localhost/auction_never_use"
os.environ["AUTO_CREATE_TABLES"] = "false"

from app.db import Base  # noqa: E402 — test environment MUST be set first
import app.models  # noqa: E402,F401 — register model tables after isolation


@pytest.fixture
def db():
    """Fresh in-memory SQL database per test, never the application's configured DB."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def actors(db):
    from app.models import User, UserRole

    seller = User(username="seller", email="seller@example.org", hashed_password="hashed", role=UserRole.SELLER)
    buyer = User(username="buyer", email="buyer@example.org", hashed_password="hashed", role=UserRole.BUYER)
    other = User(username="other", email="other@example.org", hashed_password="hashed", role=UserRole.SELLER)
    admin = User(username="admin", email="admin@example.org", hashed_password="hashed", role=UserRole.ADMIN)
    db.add_all([seller, buyer, other, admin])
    db.commit()
    return seller, buyer, other, admin

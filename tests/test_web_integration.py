"""End-to-end HTTP tests against isolated SQLAlchemy-backed test sessions."""
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
import pytest

from app.auth import create_access_token, hash_password
from app.db import get_db
from app.main import app
from app.schemas import AuctionCreate, LotCreate
from app.services import create_auction, create_lot


@pytest.fixture
def http_client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app, base_url="http://localhost", follow_redirects=False) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_health_swagger_and_authentication_gate(http_client):
    assert http_client.get("/health").json() == {"status": "ok"}
    schema = http_client.get("/openapi.json")
    assert schema.status_code == 200
    assert "/api/lots/{lot_id}/favorite" in schema.json()["paths"]
    assert "/api/users/me/favorites" in schema.json()["paths"]
    assert http_client.get("/docs").status_code == 200
    protected = http_client.get("/")
    assert protected.status_code == 303
    assert protected.headers["location"].startswith("/login?")


@pytest.mark.parametrize("identity", ["buyer", "buyer@example.org"])
def test_login_by_username_or_email_and_dashboard(http_client, db, actors, identity):
    _, buyer, _, _ = actors
    buyer.hashed_password = hash_password("CorrectPassword123")
    db.commit()
    page = http_client.get("/login")
    assert page.status_code == 200
    token = http_client.cookies.get("csrf_token")
    assert token
    login = http_client.post("/login", data={
        "identity": identity, "password": "CorrectPassword123", "csrf_token": token, "next": "/dashboard"
    })
    assert login.status_code == 303
    assert login.headers["location"] == "/dashboard"
    assert http_client.cookies.get("access_token")
    dashboard = http_client.get("/dashboard")
    assert dashboard.status_code == 200
    assert "buyer" in dashboard.text


def test_login_invalid_password_does_not_set_auth_cookie(http_client, db, actors):
    _, buyer, _, _ = actors
    buyer.hashed_password = hash_password("CorrectPassword123")
    db.commit()
    http_client.get("/login")
    wrong = http_client.post("/login", data={
        "identity": "buyer", "password": "wrong", "csrf_token": http_client.cookies.get("csrf_token")
    })
    assert wrong.status_code == 400
    assert not http_client.cookies.get("access_token")


def test_catalog_search_and_status_filter(http_client, db, actors):
    seller, buyer, _, _ = actors
    lot = create_lot(db, seller, LotCreate(title="Unique Antique Camera", start_price="100"))
    create_auction(db, seller, AuctionCreate(
        lot_id=lot.id, start_time=datetime.now() - timedelta(minutes=1),
        end_time=datetime.now() + timedelta(hours=1),
    ))
    http_client.cookies.set("access_token", create_access_token(buyer))
    visible = http_client.get("/?q=Antique&status=active")
    assert visible.status_code == 200
    assert "Unique Antique Camera" in visible.text
    absent = http_client.get("/?q=NoSuchProduct&status=active")
    assert absent.status_code == 200
    assert "Unique Antique Camera" not in absent.text

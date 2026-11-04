from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.db import get_db
from app.main import app
from app.models import LotStatus
from app.schemas import LotCreate
from app.services import create_lot


def test_favorites_api_auth_csrf_isolation(db, actors):
    seller, buyer, other, _ = actors
    lot = create_lot(db, seller, LotCreate(title="Test watch", start_price="5"))
    lot.status = LotStatus.ACTIVE
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app, base_url="http://localhost") as client:
            assert client.get("/api/users/me/favorites").status_code == 401
            client.cookies.set("access_token", create_access_token(buyer))
            assert client.put(f"/api/lots/{lot.id}/favorite").status_code == 403
            client.cookies.set("csrf_token", "a" * 32)
            header = {"X-CSRF-Token": "a" * 32}
            assert client.put(f"/api/lots/{lot.id}/favorite", headers=header).status_code == 200
            assert client.put(f"/api/lots/{lot.id}/favorite", headers=header).status_code == 200
            favorites = client.get("/api/users/me/favorites")
            assert favorites.status_code == 200
            assert [f["id"] for f in favorites.json()] == [lot.id]
            assert client.delete(f"/api/lots/{lot.id}/favorite", headers=header).status_code == 204
            assert client.get("/api/users/me/favorites").json() == []
            client.cookies.set("access_token", create_access_token(other))
            assert client.get("/api/users/me/favorites").json() == []
    finally:
        app.dependency_overrides.clear()

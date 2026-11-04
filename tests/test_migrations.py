from pathlib import Path

from alembic import command
from sqlalchemy import create_engine, inspect, text

from scripts.migrate import alembic_config, migrate_database


def test_clean_database_three_sequential_revisions(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'empty.sqlite'}"
    migrate_database(url)
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert {"users", "lots", "auctions", "sales", "favorite_lots", "alembic_version"} <= tables
        assert "condition" in {c["name"] for c in inspect(engine).get_columns("lots")}
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
    finally:
        engine.dispose()
    migrate_database(url)  # idempotent


def test_upgrade_legacy_database_preserves_rows(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'legacy.sqlite'}"
    command.upgrade(alembic_config(url), "0001")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (id, username, email, hashed_password, role, created_at) VALUES (1,'legacy','old@example.org','hashed','SELLER',CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO lots (id, title, start_price, seller_id, status, created_at) VALUES (1,'pre-existing',10,1,'DRAFT',CURRENT_TIMESTAMP)"))
        conn.execute(text("DROP TABLE alembic_version"))  # old app predates Alembic
    engine.dispose()
    migrate_database(url)
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT title, condition FROM lots WHERE id=1")).one()
            assert row == ("pre-existing", "used")
            assert conn.scalar(text("SELECT count(*) FROM users")) == 1
            assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
    finally:
        engine.dispose()


def test_incomplete_legacy_database_is_not_stamped(tmp_path: Path):
    import pytest
    url = f"sqlite:///{tmp_path / 'partial.sqlite'}"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
    engine.dispose()
    with pytest.raises(RuntimeError, match="Неполная"):
        migrate_database(url)

"""Apply Alembic revisions; safely adopt the four-table legacy schema."""
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine.url import make_url

from app.config import get_settings

CORE_TABLES = {"users", "lots", "auctions", "sales"}
LEGACY_FOREIGN_KEYS = {
    "lots": {("seller_id", "users")},
    "auctions": {("lot_id", "lots")},
    "sales": {("auction_id", "auctions"), ("buyer_id", "users")},
}
LEGACY_COLUMNS = {
    "users": {"id", "username", "email", "hashed_password", "role", "created_at"},
    "lots": {"id", "title", "description", "start_price", "seller_id", "status", "created_at"},
    "auctions": {"id", "lot_id", "start_time", "end_time", "status", "current_price"},
    "sales": {"id", "auction_id", "buyer_id", "amount", "created_at"},
}


def alembic_config(url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def migrate_database(url: str) -> None:
    if make_url(url).get_backend_name() not in {"mysql", "mariadb", "sqlite"}:
        raise ValueError("Миграции поддерживают MariaDB/MySQL; SQLite допустим только в тестах")
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        present = tables & CORE_TABLES
        has_version = "alembic_version" in tables
        if present and present != CORE_TABLES:
            raise RuntimeError("Неполная исходная схема БД. Миграция остановлена без изменений.")
        config = alembic_config(url)
        if present == CORE_TABLES and not has_version:
            for table, required in LEGACY_COLUMNS.items():
                actual = {c["name"] for c in inspector.get_columns(table)}
                if not required <= actual:
                    raise RuntimeError(f"Таблица {table} не соответствует исходной схеме: {required - actual}")
            for table, required in LEGACY_FOREIGN_KEYS.items():
                actual = {
                    (fk["constrained_columns"][0], fk["referred_table"])
                    for fk in inspector.get_foreign_keys(table)
                    if len(fk["constrained_columns"]) == 1
                }
                if not required <= actual:
                    raise RuntimeError(f"Таблица {table} имеет неправильные внешние ключи")
            if "condition" in {c["name"] for c in inspector.get_columns("lots")} or "favorite_lots" in tables:
                raise RuntimeError("Схема уже изменена, но alembic_version отсутствует; требуется ручная проверка")
            # DO NOT run initial CREATE TABLE on a legacy database with data.
            command.stamp(config, "0001")
        command.upgrade(config, "head")
    finally:
        engine.dispose()


def main() -> None:
    url = os.environ.get("DATABASE_URL") or get_settings().database_url
    migrate_database(url)
    print("База данных обновлена до последней ревизии Alembic.")


if __name__ == "__main__":
    main()

"""Fail if deployment is missing Alembic revisions."""
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.config import get_settings
from scripts.migrate import alembic_config


def main():
    url = get_settings().database_url
    engine = create_engine(url)
    try:
        config = alembic_config(url)
        head = ScriptDirectory.from_config(config).get_current_head()
        with engine.connect() as connection:
            current = MigrationContext.configure(connection).get_current_revision()
        if current != head:
            raise SystemExit(f"Миграции не применены: current={current}, expected={head}. make migrate")
        print(f"Миграции применены: {current}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

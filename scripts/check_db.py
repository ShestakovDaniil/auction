"""Small MariaDB/MySQL connectivity check using DATABASE_URL from .env."""

from sqlalchemy import text

from app.db import get_engine


def main() -> None:
    with get_engine().connect() as connection:
        version = connection.execute(text("SELECT VERSION()"))
        print("Database connection OK")
        print("Server version:", version.scalar_one())


if __name__ == "__main__":
    main()

from pathlib import Path
import secrets
from urllib.parse import quote_plus


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


def main():
    if ENV_FILE.exists():
        answer = input(".env уже существует. Перезаписать? [y/N]: ").strip().lower()

        if answer not in {"y", "yes"}:
            print("Отменено.")
            return

    print("Настройка Auction Lab")
    print()

    db_user = input("Пользователь MariaDB [auction_app]: ").strip() or "auction_app"
    db_password = input("Пароль MariaDB: ").strip()
    db_host = input("Хост MariaDB [127.0.0.1]: ").strip() or "127.0.0.1"
    db_port = input("Порт MariaDB [3306]: ").strip() or "3306"
    db_name = input("Название базы [auction_lab]: ").strip() or "auction_lab"

    encoded_user = quote_plus(db_user)
    encoded_password = quote_plus(db_password)

    secret_key = secrets.token_urlsafe(48)

    content = f"""APP_NAME=Auction Lab
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000

DATABASE_URL=mysql+pymysql://{encoded_user}:{encoded_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4
APP_SECRET_KEY={secret_key}

AUTO_CREATE_TABLES=true
ACCESS_TOKEN_EXPIRE_MINUTES=480
COOKIE_SECURE=false
MIN_BID_INCREMENT=1.00
CATALOG_PAGE_SIZE=9
ALLOWED_HOSTS=127.0.0.1,localhost
"""

    ENV_FILE.write_text(content, encoding="utf-8")

    try:
        ENV_FILE.chmod(0o600)
    except OSError:
        pass

    print()
    print(f".env создан: {ENV_FILE}")
    print("APP_SECRET_KEY сгенерирован автоматически.")


if __name__ == "__main__":
    main()

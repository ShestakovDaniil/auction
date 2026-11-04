"""Interactive first-run configuration for an existing MariaDB/MySQL server."""

from getpass import getpass
from pathlib import Path
import re
import secrets
from urllib.parse import quote_plus

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
DB_NAME_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,58}\Z")


def main() -> None:
    if ENV_FILE.exists():
        print(".env уже существует; настройки и секреты сохранены.")
        return

    print("Первоначальная настройка Auction Lab")
    print("Необходимо заранее создать рабочую и отдельную тестовую БД на MariaDB/MySQL.")
    db_user = input("Пользователь MariaDB [auction_app]: ").strip() or "auction_app"
    db_password = getpass("Пароль MariaDB (не может быть пустым): ")
    if not db_password:
        raise SystemExit("Пароль БД обязателен. Укажите пароль выделенного пользователя.")
    db_host = input("Хост MariaDB [127.0.0.1]: ").strip() or "127.0.0.1"
    if not re.fullmatch(r"[A-Za-z0-9.:-]+", db_host):
        raise SystemExit("Недопустимый хост MariaDB (используйте IP-адрес или имя узла).")
    db_port = input("Порт MariaDB [3306]: ").strip() or "3306"
    if not db_port.isdecimal() or not 1 <= int(db_port) <= 65535:
        raise SystemExit("Некорректный порт MariaDB.")
    db_name = input("Название рабочей БД [auction_lab]: ").strip() or "auction_lab"
    if not DB_NAME_PATTERN.fullmatch(db_name):
        raise SystemExit("Недопустимое имя базы: буквы, цифры, _, не более 59 символов.")
    test_db_name = db_name + "_test"

    host = f"[{db_host}]" if ":" in db_host else db_host
    auth = f"{quote_plus(db_user)}:{quote_plus(db_password)}@{host}:{db_port}"
    app_database = f"mysql+pymysql://{auth}/{db_name}?charset=utf8mb4"
    test_database = f"mysql+pymysql://{auth}/{test_db_name}?charset=utf8mb4"
    app_secret = secrets.token_urlsafe(48)
    content = f"""APP_NAME=Auction Lab
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000
DATABASE_URL={app_database}
TEST_DATABASE_URL={test_database}
APP_SECRET_KEY={app_secret}
AUTO_CREATE_TABLES=false
ACCESS_TOKEN_EXPIRE_MINUTES=480
COOKIE_SECURE=false
MIN_BID_INCREMENT=1.00
CATALOG_PAGE_SIZE=9
ALLOWED_HOSTS=127.0.0.1,localhost
"""
    ENV_FILE.write_text(content, encoding="utf-8")
    ENV_FILE.chmod(0o600)
    print(f"Создан конфигурационный файл: {ENV_FILE}")
    print(f"Проверьте, что существуют БД {db_name!r} и {test_db_name!r} и права на них.")
    print("APP_SECRET_KEY сгенерирован автоматически; тестовая БД отделена от рабочей.")


if __name__ == "__main__":
    main()

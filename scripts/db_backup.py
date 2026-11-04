"""Safe, authenticated MariaDB/MySQL logical backups and restores.

Credentials are placed in a private, short-lived option file, never in process args.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gzip
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from sqlalchemy.engine.url import make_url

from app.config import get_settings

BACKUP_DIR = Path("backups")


def parse_db(url: str):
    parsed = make_url(url)
    if parsed.drivername not in {"mysql+pymysql", "mariadb+pymysql"}:
        raise ValueError("Резервирование доступно только для MariaDB/MySQL")
    if not parsed.database or not re.fullmatch(r"[a-zA-Z0-9_]+", parsed.database):
        raise ValueError("Недопустимое имя базы данных")
    if not parsed.username or not parsed.password:
        raise ValueError("Нужно указать пользователя и пароль БД")
    return parsed


@contextmanager
def connection_options(url: str):
    parsed = parse_db(url)
    with tempfile.TemporaryDirectory(prefix="auction-db-") as tmp:
        path = Path(tmp) / "client.cnf"
        # MySQL config option-file values are double-quoted, with escaped slashes and quotes.
        def quote(value):
            return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'

        path.write_text(
            "[client]\n"
            f"user={quote(parsed.username)}\n"
            f"password={quote(parsed.password)}\n"
            f"host={quote(parsed.host or 'localhost')}\n"
            f"port={int(parsed.port or 3306)}\n"
            "protocol=tcp\n",
            encoding="utf-8",
        )
        path.chmod(0o600)
        yield parsed, path


def locate_client(*options: str) -> str:
    for name in options:
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError(f"Не найдена утилита {options}. Установите mariadb-client")


def backup_database(url: str, destination: Path | None = None) -> Path:
    with connection_options(url) as (parsed, optfile):
        dest = destination or BACKUP_DIR / f"{parsed.database}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.sql.gz"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            raise FileExistsError(f"Резервная копия уже существует: {dest}")
        client = locate_client("mariadb-dump", "mysqldump")
        cmd = [client, f"--defaults-extra-file={optfile}", "--single-transaction", "--quick", "--routines", "--triggers", "--default-character-set=utf8mb4", parsed.database]
        try:
            # Capture stderr without logging secrets or full SQL data.
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
                with dest.open("xb") as raw:
                    dest.chmod(0o600)
                    with gzip.GzipFile(fileobj=raw, mode="wb") as compressed:
                        shutil.copyfileobj(process.stdout, compressed)
                error = process.stderr.read().decode("utf-8", "replace")
                if process.wait() != 0:
                    raise RuntimeError(f"Сбой резервного копирования: {error.strip()}")
        except BaseException:
            dest.unlink(missing_ok=True)
            raise
        return dest


def restore_database(url: str, source: Path, confirmation: str) -> None:
    with connection_options(url) as (parsed, optfile):
        if confirmation != parsed.database:
            raise ValueError(f"Восстановление перезапишет {parsed.database}. Укажите CONFIRM_RESTORE={parsed.database}")
        if not source.is_file() or not source.name.endswith(".sql.gz"):
            raise ValueError("BACKUP_FILE должен указывать на существующий файл .sql.gz")
        client = locate_client("mariadb", "mysql")
        with gzip.open(source, "rb") as data:
            with subprocess.Popen([client, f"--defaults-extra-file={optfile}", f"--database={parsed.database}"], stdin=subprocess.PIPE, stderr=subprocess.PIPE) as process:
                try:
                    shutil.copyfileobj(data, process.stdin)
                    process.stdin.close()
                    error = process.stderr.read().decode("utf-8", "replace")
                    if process.wait() != 0:
                        raise RuntimeError(f"Ошибка восстановления: {error.strip()}")
                except BaseException:
                    process.kill()
                    process.wait()
                    raise


def main():
    parser = argparse.ArgumentParser(description="MariaDB logical dump/restore")
    parser.add_argument("action", choices=["backup", "restore"])
    args = parser.parse_args()
    url = os.getenv("DATABASE_URL") or get_settings().database_url
    if args.action == "backup":
        result = backup_database(url)
        print(f"Резервная копия создана: {result}")
    else:
        file_name = os.getenv("BACKUP_FILE")
        if not file_name:
            parser.error("Укажите BACKUP_FILE=backups/....sql.gz")
        restore_database(url, Path(file_name), os.getenv("CONFIRM_RESTORE", ""))
        print(f"Восстановлено из {file_name}")


if __name__ == "__main__":
    main()

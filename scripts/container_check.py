"""Lab 4: check Compose policies and prove container behavior on disposable volumes.

Uses only Python's standard library and Docker Compose. Never touches the live project.
"""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env.container"
DOCKERFILE = ROOT / "Dockerfile"
IGNORE = ROOT / ".dockerignore"
COMPOSE_FILE = ROOT / "compose.yaml"


class CheckError(RuntimeError):
    pass


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def load_env() -> dict[str, str]:
    if os.environ.get("DB_PASSWORD") and os.environ.get("APP_SECRET_KEY"):
        values = {key: os.environ[key] for key in ("DB_PASSWORD", "APP_SECRET_KEY")}
    else:
        values = read_env_file()
    password = values.get("DB_PASSWORD", "")
    secret = values.get("APP_SECRET_KEY", "")
    ensure(
        bool(re.fullmatch(r"[A-Za-z0-9_-]{16,}", password)) and "REPLACE" not in password,
        "DB_PASSWORD: задайте случайный пароль от 16 символов (буквы, цифры, - и _)",
    )
    ensure(len(secret) >= 32 and "REPLACE" not in secret, "APP_SECRET_KEY: задайте случайный ключ длиной не менее 32 символов")
    return values


def read_env_file() -> dict[str, str]:
    ensure(ENV_FILE.is_file(), "Нет .env.container: скопируйте .env.container.example и задайте секреты")
    values = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ensure("=" in line, "Неправильная строка в .env.container")
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def static_policy() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    dockerignore = IGNORE.read_text(encoding="utf-8")
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    base = re.findall(r"^FROM\s+(\S+)", dockerfile, flags=re.MULTILINE | re.IGNORECASE)
    ensure(
        len(base) == 1 and re.fullmatch(r"python:\d+\.\d+\.\d+-slim-(?:bookworm|trixie)", base[0]),
        "Dockerfile: нужен фиксированный Python patch tag; latest запрещён",
    )
    user_instruction = re.findall(r"^USER\s+(\S+)", dockerfile, re.MULTILINE | re.IGNORECASE)
    ensure(
        len(user_instruction) == 1 and user_instruction[0].split(":", 1)[0].lower() not in {"0", "root"},
        "Dockerfile: приложение должно запускаться от непривилегированного пользователя",
    )
    ensure(
        not re.search(r"^(?:ARG|ENV)\s+(?:APP_SECRET_KEY|DB_PASSWORD)\b", dockerfile, re.MULTILINE | re.IGNORECASE),
        "Dockerfile: секреты нельзя передавать при сборке",
    )
    ensure(not re.search(r"^\s*(?:COPY|ADD)\s+\.\s", dockerfile, re.MULTILINE | re.IGNORECASE), "Dockerfile: запрещено копировать весь контекст сборки")
    ensure("CMD [" in dockerfile and '--host", "0.0.0.0' in dockerfile, "Dockerfile: используйте exec-form CMD и прослушивание контейнерного интерфейса")
    ensure("HEALTHCHECK NONE" not in dockerfile.upper(), "Нельзя отключать HEALTHCHECK")
    patterns = {line.strip() for line in dockerignore.splitlines()}
    ensure({".env", ".env.*", "backups/", ".git", "tests/"} <= patterns, ".dockerignore: исключите секреты, дампы и служебные файлы")
    ensure(not re.search(r"(?:image|FROM):?\s*[^\s]+:latest\b", dockerfile + "\n" + compose, re.IGNORECASE), "Запрещён тег latest")


def check_compose(data: dict) -> None:
    services = data.get("services", {})
    ensure(set(services) == {"db", "migrate", "app"}, "Compose должен содержать только db, migrate и app")
    for name in ("db", "app"):
        check = services[name].get("healthcheck", {})
        ensure(check.get("test") and not check.get("disable", False), f"{name}: healthcheck обязателен и не должен быть отключён")
    for name in services:
        service = services[name]
        ensure(service.get("cpus") and service.get("mem_limit"), f"{name}: отсутствует лимит CPU или памяти")
        ensure(service.get("networks"), f"{name}: внутренняя сеть не настроена")
        image = service.get("image", "")
        ensure(image and not image.endswith(":latest"), f"{name}: нельзя использовать latest")
    ensure(not services["db"].get("ports") and not services["migrate"].get("ports"), "Запрещено публиковать порт БД и мигратора")
    ports = services["app"].get("ports", [])
    ensure(
        len(ports) == 1 and int(ports[0].get("target", 0)) == 8000 and ports[0].get("host_ip") in {"127.0.0.1", "172.16.10.10"},
        "Нужно публиковать только порт приложения 8000 на 127.0.0.1",
    )
    ensure(
        services["app"].get("depends_on", {}).get("migrate", {}).get("condition") == "service_completed_successfully",
        "Приложение должно ожидать завершения миграций",
    )
    ensure(services["migrate"].get("depends_on", {}).get("db", {}).get("condition") == "service_healthy", "Миграции должны ожидать здоровую БД")
    mounts = services["db"].get("volumes", [])
    ensure(any(v.get("target") == "/var/lib/mysql" and v.get("type") == "volume" for v in mounts), "Данные БД должны сохраняться в named volume")
    ensure(
        "@db:3306/auction_lab" in services["app"].get("environment", {}).get("DATABASE_URL", ""), "Контейнер должен подключаться к БД по внутреннему имени db"
    )
    ensure(services["app"].get("environment", {}).get("AUTO_CREATE_TABLES", "").lower() == "false", "AUTO_CREATE_TABLES должен оставаться false")


def call(command: list[str], *, env: dict[str, str], silent: bool = False) -> str:
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    if result.returncode:
        # Do not echo rendered Compose JSON or commands containing credentials.
        stderr = result.stderr.strip().splitlines()
        detail = stderr[-1] if stderr else "Команда завершилась с ошибкой"
        raise CheckError(f"Ошибка Docker/Compose ({command[0]}): {detail}")
    if not silent and result.stdout.strip():
        print(result.stdout.strip())
    return result.stdout.strip()


def compose(project: str, args: list[str], env: dict[str, str], *, silent: bool = False) -> str:
    return call(["docker", "compose", "--env-file", os.devnull, "-p", project, *args], env=env, silent=silent)


def python_in_app(project: str, code: str, env: dict[str, str], *, one_off: bool = False) -> str:
    prefix = ["run", "--rm", "--no-deps"] if one_off else ["exec", "-T"]
    return compose(project, [*prefix, "app", "python", "-c", code], env, silent=True)


CREATE_RECORD = """from sqlalchemy import create_engine, text
from app.config import get_settings
engine = create_engine(get_settings().database_url)
with engine.begin() as connection:
    connection.execute(text('CREATE TABLE IF NOT EXISTS lab4_check (id INTEGER PRIMARY KEY, marker VARCHAR(64) NOT NULL)'))
    connection.execute(text("INSERT INTO lab4_check (id, marker) VALUES (1, 'kept-after-recreate') ON DUPLICATE KEY UPDATE marker = VALUES(marker)"))
engine.dispose()
"""

VERIFY_RECORD = """from sqlalchemy import create_engine, text
from app.config import get_settings
engine = create_engine(get_settings().database_url)
with engine.connect() as connection:
    marker = connection.execute(text('SELECT marker FROM lab4_check WHERE id = 1')).scalar_one()
assert marker == 'kept-after-recreate', marker
engine.dispose()
"""


def run_live_checks(env: dict[str, str]) -> None:
    # Unique project names ensure the running app and its data volume remain untouched.
    suffix = uuid4().hex[:12]
    check_project = f"auction-lab4-check-{suffix}"
    restore_project = f"auction-lab4-restore-{suffix}"
    check_active = False
    restore_active = False
    try:
        print("[1/6] Сборка контейнерного образа")
        if not env.get("AUCTION_CHECK_IMAGE"):
            compose(check_project, ["build", "app", "migrate"], env, silent=True)
        print("[2/6] Запуск изолированного окружения, ожидание healthcheck и миграций")
        check_active = True
        compose(check_project, ["up", "-d", "--wait", "--no-build"], env, silent=True)
        python_in_app(check_project, "import os; assert os.geteuid() == 10001", env)
        compose(check_project, ["exec", "-T", "app", "python", "-m", "scripts.check_migration_state"], env, silent=True)
        print("[3/6] Проверка данных после пересоздания контейнеров")
        python_in_app(check_project, CREATE_RECORD, env)
        compose(check_project, ["up", "-d", "--wait", "--no-build", "--force-recreate"], env, silent=True)
        python_in_app(check_project, VERIFY_RECORD, env)
        print("[4/6] Проверка корректного завершения по SIGTERM")
        container_id = compose(check_project, ["ps", "-a", "-q", "app"], env, silent=True)
        ensure(container_id, "Контейнер приложения не найден")
        compose(check_project, ["stop", "-t", "20", "app"], env, silent=True)
        exit_code = call(["docker", "inspect", "--format", "{{.State.ExitCode}}", container_id], env=env, silent=True)
        logs = compose(check_project, ["logs", "--no-color", "app"], env, silent=True)
        ensure(exit_code in {"0", "143"} and "Finished server process" in logs, f"Приложение не завершилось корректно по SIGTERM (exit={exit_code})")
        # Start again to exercise the existing Lab 3 backup script.
        compose(check_project, ["up", "-d", "--wait", "--no-build"], env, silent=True)
        print("[5/6] Создание SQL-дампа в named volume")
        result = compose(check_project, ["exec", "-T", "app", "python", "-m", "scripts.db_backup", "backup"], env, silent=True)
        filename_match = re.search(r"backups/(auction_lab-\d{8}T\d{6}Z\.sql\.gz)", result)
        ensure(filename_match is not None, "Не удалось получить имя файла резервной копии")
        filename = filename_match.group(1)
        # Release RAM before starting another MariaDB. The original backup volume stays intact.
        compose(check_project, ["stop"], env, silent=True)
        print("[6/6] Восстановление SQL-дампа в новый volume и проверка содержимого")
        restore_active = True
        compose(restore_project, ["up", "-d", "--wait", "--no-build", "db"], env, silent=True)
        # Read the backup from the original named volume with its original owner/mode (0600).
        # No host copy and no relaxation of backup file permissions is needed.
        compose(
            restore_project,
            [
                "run",
                "--rm",
                "--no-deps",
                "--volume",
                f"{check_project}_backups:/opt/auction/import:ro",
                "-e",
                f"BACKUP_FILE=/opt/auction/import/{filename}",
                "-e",
                "CONFIRM_RESTORE=auction_lab",
                "app",
                "python",
                "-m",
                "scripts.db_backup",
                "restore",
            ],
            env,
            silent=True,
        )
        python_in_app(restore_project, VERIFY_RECORD, env, one_off=True)
        compose(restore_project, ["run", "--rm", "--no-deps", "app", "python", "-m", "scripts.check_migration_state"], env, silent=True)
    finally:
        if restore_active:
            compose(restore_project, ["down", "-v", "--remove-orphans"], env, silent=True)
        if check_active:
            compose(check_project, ["down", "-v", "--remove-orphans"], env, silent=True)


def main() -> int:
    try:
        values = load_env()
        static_policy()
        ensure(
            subprocess.run(["docker", "compose", "version"], capture_output=True, check=False).returncode == 0,
            "Docker Compose v2 не установлен или Docker недоступен",
        )
        env = os.environ.copy()
        env.update(values, APP_BIND_IP="127.0.0.1", APP_HOST_PORT="0")
        config = compose("auction-lab4-check-config", ["config", "--format", "json"], env, silent=True)
        check_compose(json.loads(config))
        run_live_checks(env)
    except (CheckError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"container-check: FAIL: {exc}", file=sys.stderr)
        return 1
    print("container-check: OK — образ, политики, healthcheck, миграции, UID, SIGTERM, volume и restore")
    return 0


if __name__ == "__main__":
    sys.exit(main())

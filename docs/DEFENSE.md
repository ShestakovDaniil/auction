# Защита лабораторной №3 — воспроизводимый сценарий

## 0. Подготовка

Убедитесь, что в `.env` отдельно указаны `DATABASE_URL` и `TEST_DATABASE_URL`, причем
тестовая БД имеет суффикс `_test`. Сервер MariaDB/MySQL должен быть доступен
по адресу из конфигурации, а пользователь БД — иметь права на обе базы.
Запуск команды `make verify` должен завершиться строкой `all checks passed`.

## 1. Что запускает make verify?

1. `ruff format --check` — не допускает неформатированный Python-код.
2. `ruff check` — линтер, импорт и синтаксические нарушения.
3. `bandit -r app scripts -ll -ii` — SAST на medium/high находки с достаточной уверенностью.
4. `pytest` — unit, API и интеграционные тесты (в том числе MariaDB).
5. `--cov-branch --cov-fail-under=40` — замер покрытия с запретом падения ниже 40%; XML/HTML/JUnit.
6. `mutation-check` — подменяет `+` на `-` в изолированной копии правила ставки и убеждается,
   что **реальный pytest** выявляет регрессию.
7. `check_migration_state` — сверяет фактическую ревизию рабочей БД с Alembic head.
8. `compileall` — проверяет синтаксис файлов пакета.

## 2. Преподаватель меняет условие

Открыть `app/domain.py`, заменить `current_highest + min_increment` на
`current_highest - min_increment`. Выполнить `make test-local`:
`tests/test_domain.py::test_bid_minimum` должен упасть. Вернуть `+`, проверить снова.
Независимо можно запустить `make mutation-check` без ручного изменения рабочего дерева.

## 3. Чистая и заполненная MariaDB

`make test-mariadb` (или `make verify`) повторяет оба сценария на отдельной БД:

- с нуля до 0003 (проверка пяти таблиц);
- заполненная исходная БД со схемой 0001 без `alembic_version` → распознавание legacy,
  stamp 0001, upgrade 0002 + 0003 и сохранение строки `lots.title='original'`.

На рабочей БД `make migrate` можно повторять: операция идемпотентна.

## 4. Порча и восстановление

Интеграционный тест `tests/test_mariadb.py::test_mariadb_legacy_upgrade_and_restore` сам
создаёт дамп, изменяет `lots.title` на `CORRUPTED`, восстанавливает дамп и проверяет
возврат `original`. Он не трогает обычную `auction_lab`.

Для ручной демонстрации на **учебной** БД:

```bash
make backup
# Запомнить путь, который вывела команда.
# Изменить тестовую строку через mysql/mariadb-клиент.
BACKUP_FILE=backups/ИМЯ_ДАМПА.sql.gz CONFIRM_RESTORE=auction_lab make restore
```

**Перед ручным восстановлением проверьте, что `.env` указывает на демонстрационную БД.**

## 5. Изменение функциональности

Добавлены избранные лоты (Alembic 0003, FavoriteLot, API, CSRF, тесты).
После любого дальнейшего изменения: `make format`, `make verify`. Изменение не принимается,
если хотя бы одна проверка не прошла.

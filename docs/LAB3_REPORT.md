# Отчет — лабораторная работа №3 (Auction Lab)

## Что изменено относительно исходного архива

| № | Требование | Реализация / доказательство |
| --- | --- | --- |
| 1 | Единая настройка | `make setup`, `scripts/setup_env.py`, `.env.example` |
| 2 | Фиксированные версии | `requirements.txt`, `requirements-dev.txt` |
| 3 | Унифицированные команды | `Makefile`: setup/run/test/quality/migrate/backup/restore/verify |
| 4 | Unit и интеграционные тесты | `tests/test_domain.py`, `test_services.py`, `test_api.py`, `test_migrations.py`, `test_mariadb.py`, `test_setup_env.py` |
| 5 | Ошибки и границы, мутационный тест | Граничные и негативные тесты + `scripts/mutation_check.py` |
| 6 | Изолированная конфигурация | `tests/conftest.py`, SQLite in-memory, TEST_DATABASE_URL и строгий guard `_test` |
| 7 | Форматирование, SAST, отчеты | Ruff, Bandit, `reports/junit.xml`, `reports/coverage.xml`, HTML coverage |
| 8 | Три ревизии | 0001 → 0002 → 0003 в `alembic/versions/` |
| 9 | Чистая/заполненная БД | `test_migrations.py`, `test_mariadb.py`, `scripts/migrate.py` |
| 10 | Новая функция | Избранные лоты, таблица `favorite_lots`, 3 новых API маршрута |
| 11 | Backup/restore | `scripts/db_backup.py`, make backup/restore |
| 12 | Восстановление после порчи | `tests/test_mariadb.py::test_mariadb_legacy_upgrade_and_restore` |
| 13 | Единый набор | `make verify` |
| 14 | Антиобход правил | `docs/QA_POLICY.md`, проверяемый порог 40%, отсутствие skip в маркере MariaDB |
| 15 | Функциональная доработка с проверкой | Избранные лоты + тесты; результат полного verify требует реальной MariaDB |

### Соответствие функциональным требованиям ТЗ

Автоматизированы сценарии: публичная регистрация покупателей и продавцов, запрет регистрации
админа, дубликат пользователя, создание лотов и проверка ролей, исходный статус draft,
право владения, интервал аукциона, запрет двух открытых аукционов лота, первая и следующая ставки,
временные границы, запрет собственной ставки, завершение и запрет ставок после завершения,
подсчет максимальной ставки и tie-break, объектная видимость избранного, CSRF/аутентификация API.
Общий охват бизнес-правил из описания проекта — **более 40% по матрице сценариев**;
программное покрытие вычисляется отдельно инструментом coverage.

### Фактическое выполнение в текущем окружении

- `pytest -m 'not mariadb'`: **62 теста успешно**, проверены миграции чистой и заполненной SQLite, а также создание `.env` с обычным подключением к MariaDB.
- `pytest --cov=app --cov-branch -m 'not mariadb'`: **81.85% покрытия Python** (порог 40%).
- `python -m scripts.mutation_check`: **пройдено**, тесты обнаруживают мутацию шага ставки.
- **Ограничение:** в среде сборки отсутствуют MariaDB server/client, PyMySQL, Ruff, Bandit,
  а загрузка пакетов извне недоступна. Поэтому реальные MariaDB миграции, backup/restore
  и `make verify` полностью **не выполнялись**. Это НЕ объявляется успешным `make verify`.
- Для закрытия пункта 15 и фактической демонстрации восстановления необходимо выполнить
  `make setup && make verify` в Debian с доступной MariaDB/MySQL и сохранить
  отчеты, а не подменять их локальным тестом SQLite.

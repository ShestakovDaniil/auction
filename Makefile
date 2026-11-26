SHELL := /bin/bash
.DEFAULT_GOAL := help
PYTHON := .venv/bin/python
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
RUFF := .venv/bin/ruff
BANDIT := .venv/bin/bandit
RUFF_FLAGS ?=
BANDIT_FLAGS ?=

.PHONY: help setup run format mutation-check test test-local test-mariadb quality migrate backup restore verify container-check container-up container-down container-backup container-restore container-migrate migration-state compile-check

help:
	@echo 'setup run test quality migrate backup restore verify container-check container-up container-down container-migrate container-backup container-restore'

setup:
	python3 -m venv .venv
	$(PIP) install -r requirements-dev.txt
	@if [ ! -f .env ]; then $(PYTHON) -m scripts.setup_env; fi
	$(MAKE) format
	$(PYTHON) -m scripts.check_db
	$(MAKE) migrate

format:
	$(RUFF) format app scripts tests alembic

run:
	$(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# All unit, SQLite integration and MariaDB integration tests; failed or missing DB is fatal.
test:
	@mkdir -p reports
	$(PYTEST) --junitxml=reports/junit.xml --cov=app --cov-branch --cov-report=term-missing --cov-report=xml:reports/coverage.xml --cov-report=html:reports/coverage --cov-fail-under=40

# Useful when working offline without MariaDB; NOT a substitute for make verify.
test-local:
	@mkdir -p reports
	$(PYTEST) -m 'not mariadb' --junitxml=reports/junit-local.xml --cov=app --cov-branch --cov-report=term-missing

test-mariadb:
	$(PYTEST) -m mariadb -v

mutation-check:
	$(PYTHON) -m scripts.mutation_check

quality:
	$(RUFF) format --check app scripts tests alembic
	$(RUFF) check $(RUFF_FLAGS) app scripts tests alembic
	$(BANDIT) -r app scripts -x tests -ll -ii $(BANDIT_FLAGS)

migrate:
	$(PYTHON) -m scripts.migrate

backup:
	$(PYTHON) -m scripts.db_backup backup

restore:
	$(PYTHON) -m scripts.db_backup restore

# Never replace this sequence with '|| true', skipped tests or lower coverage gates.
verify: quality test mutation-check migration-state compile-check
	@echo 'make verify: all checks passed'

migration-state:
	$(PYTHON) -m scripts.check_migration_state

compile-check:
	$(PYTHON) -m compileall -q app scripts alembic tests


# Lab 4. The test uses isolated Compose projects and removes ONLY their volumes.
# A live deployment is allowed only after all checks complete successfully.
COMPOSE := docker compose --env-file .env.container

container-check:
	python3 -m scripts.container_check

container-up: container-check
	$(COMPOSE) up -d --wait --no-build

container-down:
	$(COMPOSE) down

container-migrate: container-check
	$(COMPOSE) run --rm --no-deps migrate

container-backup:
	$(COMPOSE) exec -T app python -m scripts.db_backup backup

# Restore requires BACKUP_FILE and CONFIRM_RESTORE=auction_lab; uses Lab 3 confirmation gate.
container-restore: container-check
	$(COMPOSE) exec -T -e BACKUP_FILE="$(BACKUP_FILE)" -e CONFIRM_RESTORE="$(CONFIRM_RESTORE)" app python -m scripts.db_backup restore

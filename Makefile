SHELL := /bin/bash
.DEFAULT_GOAL := help
PYTHON := .venv/bin/python
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
RUFF := .venv/bin/ruff
BANDIT := .venv/bin/bandit

.PHONY: help setup run format mutation-check test test-local test-mariadb quality migrate backup restore verify

help:
	@echo 'setup run test quality migrate backup restore verify'

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
	$(RUFF) check app scripts tests alembic
	$(BANDIT) -r app scripts -x tests -ll -ii

migrate:
	$(PYTHON) -m scripts.migrate

backup:
	$(PYTHON) -m scripts.db_backup backup

restore:
	$(PYTHON) -m scripts.db_backup restore

# Never replace this sequence with '|| true', skipped tests or lower coverage gates.
verify: quality test mutation-check
	$(PYTHON) -m scripts.check_migration_state
	$(PYTHON) -m compileall -q app scripts alembic tests
	@echo 'make verify: all checks passed'


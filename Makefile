.PHONY: install dev \
        lint lint-fix format format-check \
        typecheck test test-cov check \
        db-up db-down migrate revision \
        alembic-check audit \
        pre-commit-install pre-commit

install:
	uv sync

dev:
	uv run fastapi dev

lint:
	uv run ruff check .

lint-fix:
	uv run ruff check --fix .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy .

test:
	uv run pytest

test-cov:
	uv run pytest --cov=. --cov-report=term-missing

check: lint format-check typecheck test

db-up:
	docker compose up -d db

db-down:
	docker compose down -v

migrate:
	uv run alembic upgrade head

revision:
	uv run alembic revision --autogenerate -m "$(m)"

alembic-check:
	uv run alembic check

audit:
	uv audit --frozen

pre-commit-install:
	uv run pre-commit install

pre-commit:
	uv run pre-commit run --all-files

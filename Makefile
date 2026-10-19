.PHONY: install dev lint typecheck test migrate run worker up down fmt

PY ?= python

install:
	pip install -e ".[all]"

dev: install

fmt:
	ruff format app tests
	ruff check --fix app tests

lint:
	ruff check app tests
	ruff format --check app tests

typecheck:
	mypy app

test:
	pytest

check: lint typecheck test

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "$(m)"

run:
	uvicorn app.main:app --reload --port 8000

worker:
	$(PY) -m app.workflows.worker

up:
	docker compose up -d

down:
	docker compose down

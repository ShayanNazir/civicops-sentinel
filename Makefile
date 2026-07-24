.PHONY: setup up down logs test lint format migrate seed reset

setup:
	@test -f .env || cp .env.example .env
	@echo "Created .env. Review it before starting the stack."

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api

test:
	docker compose run --rm api uv run pytest

lint:
	docker compose run --rm api uv run ruff check .

format:
	docker compose run --rm api uv run ruff format .
	docker compose run --rm api uv run ruff check --fix .

migrate:
	docker compose run --rm api uv run alembic upgrade head

seed:
	docker compose exec api uv run python scripts/seed_sample_incidents.py

reset:
	docker compose down -v

# CivicOps Sentinel

A production-oriented multimodal incident intelligence platform for city operations.

This starter is **Sprint 1: the reliable ingestion foundation**. It intentionally does not add
LLMs yet. We first establish typed APIs, persistent storage, health checks, migrations, testing,
and a reproducible local environment.

## What Sprint 1 includes

- FastAPI service
- PostgreSQL with pgvector installed
- Redis
- SQLAlchemy async persistence
- Alembic migrations
- Incident create/list/get endpoints
- Liveness and readiness endpoints
- Request IDs
- Docker Compose
- Ruff and pytest
- GitHub Actions CI
- Sample data seeding script

## Start locally

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- API documentation: http://localhost:8000/docs
- Liveness: http://localhost:8000/api/v1/health/live
- Readiness: http://localhost:8000/api/v1/health/ready

In a second terminal:

```bash
docker compose exec api uv run python scripts/seed_sample_incidents.py
docker compose run --rm api uv run pytest
docker compose run --rm api uv run ruff check .
```

## Create an incident manually

```bash
curl -X POST http://localhost:8000/api/v1/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "source": "manual",
    "description": "Large fallen tree blocking one traffic lane after a storm.",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "media_urls": []
  }'
```

## Sprint 1 definition of done

- `docker compose up --build` starts all services.
- `/api/v1/health/ready` returns HTTP 200.
- An incident can be created and retrieved.
- Tests and lint checks pass.
- The first GitHub release/tag is `v0.1.0`.

See `docs/roadmap.md` for the complete build sequence.

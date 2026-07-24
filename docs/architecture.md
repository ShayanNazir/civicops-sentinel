# Architecture: Sprint 1

```text
Client
  |
  v
FastAPI API
  |-------------------> Redis readiness check
  |
  v
Repository layer
  |
  v
SQLAlchemy async session
  |
  v
PostgreSQL + pgvector
```

## Boundaries

- `api/`: HTTP transport only
- `schemas/`: request and response contracts
- `repositories/`: persistence operations
- `models/`: database representation
- `core/`: configuration and cross-cutting concerns
- `scripts/`: one-off developer and data tasks
- `tests/`: fast regression checks

Later sprints will add separate `integrations/`, `retrieval/`, `agents/`,
`evaluation/`, and `workers/` packages rather than mixing those concerns into routes.

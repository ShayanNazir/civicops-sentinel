# ADR-001: Docker-first local development

## Status

Accepted

## Context

The project depends on PostgreSQL, pgvector, Redis, and eventually background workers.
Installing these independently on each developer machine creates environment drift.

## Decision

Use Docker Compose as the default local development path. Keep the Python application
runnable outside Docker for debugging, but document Docker as the reproducible baseline.

## Consequences

- New contributors can start the stack with one command.
- CI and local environments are closer.
- Docker knowledge becomes part of the portfolio.
- Initial builds are slower than a pure local Python setup.

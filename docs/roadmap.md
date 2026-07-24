# CivicOps Sentinel Roadmap

## Sprint 1 — Reliable ingestion foundation

**Goal:** Receive and persist typed incident reports.

- [x] FastAPI service
- [x] PostgreSQL and pgvector
- [x] Redis
- [x] Alembic migrations
- [x] Incident CRUD foundation
- [x] Health checks
- [x] Request IDs
- [x] CI, linting, and tests
- [ ] Run locally and capture screenshots
- [ ] Push `v0.1.0` to GitHub

## Sprint 2 — Real-world data ingestion

**Goal:** Backfill and continuously ingest NYC 311 incidents.

- [ ] Socrata API client with pagination
- [ ] Retry, timeout, and rate-limit handling
- [ ] Raw-data landing zone
- [ ] Idempotent upsert by external ID
- [ ] Data-quality validation
- [ ] Scheduled ingestion worker
- [ ] Integration tests using recorded responses
- [ ] Basic incident analytics notebook

## Sprint 3 — Geospatial and context enrichment

**Goal:** Add weather and nearby-asset context.

- [ ] NWS client
- [ ] OpenStreetMap/Overpass client
- [ ] PostGIS migration
- [ ] Nearby-assets query
- [ ] Spatiotemporal duplicate detection baseline
- [ ] Context provenance records

## Sprint 4 — Document ingestion and hybrid RAG

**Goal:** Ground recommendations in public works manuals.

- [ ] PDF ingestion
- [ ] Text chunks and page images
- [ ] Embeddings in pgvector
- [ ] BM25/full-text search
- [ ] Reciprocal-rank fusion
- [ ] Reranking
- [ ] Citation objects
- [ ] Retrieval benchmark

## Sprint 5 — Multimodal perception

**Goal:** Analyze incident photos and voice notes.

- [ ] Image-text-to-text baseline
- [ ] Zero-shot object detection
- [ ] Segmentation for affected area
- [ ] Audio transcription
- [ ] Structured observation schema
- [ ] Model-comparison benchmark

## Sprint 6 — LangGraph orchestration

**Goal:** Combine deterministic tools and bounded agent reasoning.

- [ ] Typed graph state
- [ ] Intake node
- [ ] Perception node
- [ ] Context node
- [ ] Retrieval node
- [ ] Planning node
- [ ] Evidence verifier
- [ ] Human approval interrupt
- [ ] Durable checkpoints
- [ ] Failure recovery tests

## Sprint 7 — Evaluation and LLMOps

**Goal:** Prevent silent regressions.

- [ ] Golden evaluation set
- [ ] Retrieval metrics
- [ ] Groundedness and citation metrics
- [ ] Tool-call accuracy
- [ ] Prompt-injection tests
- [ ] Cost and latency tracking
- [ ] CI quality gates
- [ ] Trace replay

## Sprint 8 — Scale, deploy, and present

**Goal:** Make the project credible as a production system.

- [ ] Async queue
- [ ] Worker autoscaling
- [ ] Object storage
- [ ] OpenTelemetry
- [ ] Grafana dashboard
- [ ] Load tests
- [ ] Cloud deployment
- [ ] Threat model
- [ ] Architecture decision records
- [ ] Demo video
- [ ] Engineering case study

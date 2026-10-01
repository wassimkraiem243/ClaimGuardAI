# API — Layered architecture (FastAPI)

```
routers/           HTTP adapters (FastAPI routes, API key)
services/          Application use cases (ingest, dashboard, analysis, …)
domain/            ClaimPackage + ports (format-agnostic contracts)
mappers/           Pure normalization (dates, codes, gender, numbers)
repositories/    Database access (SQLAlchemy)
infrastructure/  Parsers (CSV, FHIR), Ollama, pgvector knowledge retrieval
db/                ORM models and session factory
```

## Dependency rule

- **routers** call **services** only.
- **services** use **repositories** and **infrastructure**; no raw HTTP in services.
- **repositories** map SQLAlchemy models; no FastAPI imports.

## ClaimGuard roadmap (planning)

**Implemented:** CSV + FHIR R4 Bundle → `ClaimPackage` via `POST /claims/ingest` (see `docs/architecture/data-flow.md`).

**Next:** persist ingested claims, JSONL envelope adapter (student pack), resolve `policy_id` → **15 rule results** (`result.schema.json`) → optional **explanation helper** → **audit ledger** → review events.

Implement under `app/services/` (use cases) and `app/infrastructure/` (rule catalogue loader, audit). Rule semantics and baseline: `ClaimGuardAI_Student_Starter_Pack/`.

Diagrams: `docs/architecture/`. DTOs should mirror pack schemas in `packages/shared-types`.

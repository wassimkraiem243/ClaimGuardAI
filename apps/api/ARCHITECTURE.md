# API — Layered architecture (FastAPI)

```
routers/           HTTP adapters (FastAPI routes, API key)
services/          Application use cases
repositories/    Database access (SQLAlchemy)
infrastructure/  Ollama, pgvector knowledge retrieval
db/                ORM models and session factory
```

## Dependency rule

- **routers** call **services** only.
- **services** use **repositories** and **infrastructure**; no raw HTTP in services.
- **repositories** map SQLAlchemy models; no FastAPI imports.

## ClaimGuard roadmap

Add Python modules under `app/services/` (use cases) and `app/infrastructure/` (FHIR, rules, audit persistence helpers).

Shared HTTP contracts with the UI live in `packages/shared-types` (TypeScript DTOs).

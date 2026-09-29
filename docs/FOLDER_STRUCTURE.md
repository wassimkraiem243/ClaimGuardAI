# Repository folder guide (team)

Use this map when adding data, docs, or new code. **Do not commit real PHI/PII** — only synthetic challenge datasets.

## Layout (canonical tree)

```
ClaimGuardAI/
├── apps/
│   ├── api/                 # FastAPI backend (Python)
│   └── web/                 # Next.js UI (npm workspace)
├── packages/
│   └── shared-types/        # Shared API/UI TypeScript DTOs (npm workspace)
├── data/                    # Synthetic claims, rules, benchmark inputs
├── docs/                    # Challenge brief, architecture, security, evaluation
├── scripts/                 # Dev helpers (prepare-dev, clean cache)
├── docker-compose.yml       # Postgres (pgvector)
├── package.json             # npm workspaces + `npm run dev`
├── PROJECT_REFERENCE.md
└── README.md
```

Runnable applications live under **`apps/`**. Shared frontend types live under **`packages/`**. There is no `services/` or Turborepo layer.

## Top level

| Path | Purpose | What to put here |
|------|---------|------------------|
| `apps/api/` | FastAPI backend | HTTP APIs, SQL migrations, FHIR parsers, rule engine, audit log, Ollama adapters |
| `apps/web/` | Next.js reviewer / operator UI | Dashboard, validation list, HITL review queues, rule admin (bonus) |
| `packages/shared-types/` | Shared TypeScript DTOs | `ValidationFinding`, `ClaimPackage`, API contracts |
| `data/` | **Versioned synthetic inputs** (git) | FHIR bundles, CSV exports, payer rule YAML/JSON, benchmark labels |
| `docs/` | Human-readable deliverables | Architecture diagrams, evaluation reports, security notes, challenge brief |
| `scripts/` | Repo automation | Dev bootstrap (`prepare-dev.mjs`), cache cleanup (`clean-dev-cache.mjs`) |
| `docker-compose.yml` | Local infra | Postgres (pgvector) |

## `data/` (synthetic only)

| Path | Contents |
|------|----------|
| `data/synthetic-claims/fhir/` | One file per claim or per bundle (`Claim`, `Patient`, `Coverage`, …) |
| `data/synthetic-claims/csv/` | Tabular exports if the challenge provides CSV |
| `data/payer-rules/` | Fictional payer catalogue (10–15 rules); prefer machine-readable JSON/YAML + short README |
| `data/evaluation/benchmark/` | The 50-claim validation set + ground-truth labels for F1 scoring |
| `data/attachments/samples/` | Synthetic PDFs/images for optional OCR/RAG (no real clinical notes) |

**Large files:** use Git LFS or external storage + download script; document in `data/README.md`.

## `apps/api/` — backend code

| Path | Purpose |
|------|---------|
| `app/services/` | Use cases (claims ingest, rules, audit) |
| `app/infrastructure/` | FHIR parsers, rule catalogue, Ollama, pgvector |
| `app/repositories/` | Postgres access |
| `knowledge/` | Markdown/policy chunks for RAG |
| `db/migrations/` | Ordered SQL migrations |
| `scripts/` | `apply_migrations.py`, `seed.py` |

## `docs/` deliverables (challenge checklist)

| Path | Deliverable |
|------|-------------|
| `docs/architecture/` | Diagrams (C4, data flow, sequence: ingest → rules → explain → audit) |
| `docs/challenge/` | Official brief + reference material (`CSTAM_VELODOC_BRIEF.md`, `cstamBook.txt`) |
| `docs/deliverables/video/` | Script/storyboard; link to hosted demo video |
| `docs/security/` | Threat model, RBAC, data minimization, prompt safety |
| `docs/evaluation/` | Phase 2 metrics report (F1, FPR, latency) |

## Environment & secrets

| Location | Notes |
|----------|--------|
| `apps/api/.env` | Local only — copy from `.env.example`; never commit |
| API keys | `API_KEY` for service-to-service; rotate for demos |

## Local cache cleanup

If you see a **`.turbo`** folder (leftover from an old setup), delete it or run:

```bash
npm run clean
```

## Git

Add your team remote when publishing; never commit `.env` or PHI/PII.

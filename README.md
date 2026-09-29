# ClaimGuard AI

Human-supervised agentic copilot for **healthcare claim pre-validation** (CSTAM-VELODOC × Velodoc Amazit).

Monorepo for **ClaimGuard AI**: **FastAPI** backend (`apps/api`), **Next.js** UI (`apps/web`), shared DTOs (`packages/shared-types`), Postgres (pgvector), and LLM-assisted explanations. Claim ingestion (FHIR), payer rules, and the full audit log are **in progress** — see [PROJECT_REFERENCE.md](PROJECT_REFERENCE.md) for status and conventions.

## Quick links

| Document | Description |
|----------|-------------|
| [PROJECT_REFERENCE.md](PROJECT_REFERENCE.md) | Architecture, ports, env, API plan — **start here for development** |
| [docs/challenge/CSTAM_VELODOC_BRIEF.md](docs/challenge/CSTAM_VELODOC_BRIEF.md) | Official challenge requirements & scoring |
| [docs/FOLDER_STRUCTURE.md](docs/FOLDER_STRUCTURE.md) | What to put in each folder (data, code, deliverables) |

## Prerequisites

- Node.js ≥ 18, npm 10+
- Python ≥ 3.11
- Docker or Podman (Postgres)

## First-time setup

```bash
npm install

docker compose up -d

cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/apply_migrations.py
python scripts/seed.py
cd ../..

npm run dev
```

| App | URL |
|-----|-----|
| UI | http://localhost:4000 |
| API | http://localhost:4001 |

API requests use header `x-api-key: dev-local-key` (see `apps/api/.env`).

## Repository layout

```
apps/
  api/    FastAPI (Python)
  web/    Next.js (npm workspace)
packages/
  shared-types/
```

- `data/` — synthetic claims, payer rules, benchmark sets  
- `docs/` — architecture, security, evaluation, challenge brief  

Root `package.json` uses **npm workspaces** for `apps/web` and `packages/shared-types` only. Run **`npm run clean`** if a stale **`.turbo`** folder appears (old Turborepo cache; not used anymore).

Do not commit `apps/api/.env` or real patient data.

## Challenge snapshot

**Phase 1:** ingest FHIR/CSV → rule engine (10–15 rules) → structured findings → audit log.  
**Phase 2:** benchmark 50 claims (F1), human-in-the-loop, security/privacy guards.

Details: [docs/challenge/CSTAM_VELODOC_BRIEF.md](docs/challenge/CSTAM_VELODOC_BRIEF.md).

## License / data

Use only **synthetic** claim data in this repo unless Velodoc provides explicit datasets and sharing rules.

# ClaimGuard AI

Human-supervised agentic copilot for **healthcare claim pre-validation** (CSTAM-VELODOC × Velodoc Amazit).

Monorepo: **FastAPI** (`apps/api`), **Next.js** (`apps/web`), shared DTOs (`packages/shared-types`), Postgres (pgvector). Ingest synthetic claims (JSONL, pack CSV zip, FHIR), normalize to the teaching claim envelope, run **R001–R015**, optional LLM on seeded dashboard findings.

Details for developers: [PROJECT_REFERENCE.md](PROJECT_REFERENCE.md) · Challenge brief: [docs/challenge/CSTAM_VELODOC_BRIEF.md](docs/challenge/CSTAM_VELODOC_BRIEF.md)

## Prerequisites

- Node.js ≥ 18, npm 10+
- Python ≥ 3.11
- Docker or Podman (Postgres for dashboard / seed data)
- Optional: [Ollama](https://ollama.com) for LLM finding analysis on `/findings`

## Install and run

From the repository root:

```bash
npm install

docker compose up -d

cd apps/api
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
python scripts/apply_migrations.py
python scripts/seed.py
cd ../..

npm run dev
```

| Service | URL |
|---------|-----|
| Web UI | http://localhost:4000 |
| API (OpenAPI) | http://localhost:4001/docs |
| **Phase 1 demo flow** | http://localhost:4000/phase1 |

API requests need header **`x-api-key: dev-local-key`** (default in `apps/api/.env` and `NEXT_PUBLIC_API_KEY` for the web app).

### Phase 1 user flow (UI)

1. Open **Phase 1 flow** in the sidebar.
2. **Ingest** a file: `.jsonl` (pack envelope), `.zip` (pack `csv/` folder), or `.json` (pack FHIR bundle / single envelope).
3. Review the normalized **envelope**, then **Run validation** → 15 rule results.
4. Optional: **Load rule catalog**; use **Validations** (`/findings`) for seeded findings + LLM explain (Ollama).

### API-only (curl / Swagger)

| Step | Method | Path |
|------|--------|------|
| Ingest | `POST` | `/claims/ingest` (multipart `file`) |
| Validate | `POST` | `/v1/validate` body `{ "claim": <envelope> }` |
| Rules | `GET` | `/v1/rules` |
| Policy | `GET` | `/v1/policies/{policy_id}` |

Synthetic evaluation data: `data/evaluation/development/` (claims, expected results, CSV, FHIR bundles). Rule catalogue: `data/payer-rules/`.

## Phase 2 — integration, benchmark, HITL, security

| Deliverable | Location |
|-------------|----------|
| Evaluation report (F1, false-alarm rate, latency) | `docs/evaluation/EVALUATION_REPORT.md` (+ `metrics.json`) |
| Privacy & security note | `docs/security/PRIVACY_AND_SECURITY.md` |
| Validation split (50 claims) | `data/evaluation/validation/` (generate below) |
| Reviewer routing & decisions | `POST /v1/reviews/route`, `POST /v1/reviews/decisions` (reviewer key) |

Regenerate the validation split and evaluation report:

```bash
python scripts/materialize_validation_split.py
cd apps/api
python scripts/make_eval_report.py
```

HITL smoke test (after `npm run dev`):

1. `POST /v1/validate` with a claim envelope (`x-api-key: dev-local-key`).
2. `POST /v1/reviews/route` with the same envelope → inspect `queue` / `escalation_*`.
3. `POST /v1/reviews/decisions` with `x-api-key: reviewer-dev-key` (see `.env.example`) and `original_status` matching the validated row.

## Tests

```bash
cd apps/api
.venv\Scripts\activate
python -m pytest tests/ -q
```

Pack gold scoring (optional): generate predictions with the rule engine, then use the official pack `src/evaluate.py` against `data/evaluation/development/expected_results.jsonl` (see pack doc `06_Setup_and_First_Run.md`).

## Repository layout

```
apps/api/          FastAPI — ingest, rule engine, validation, audit hook
apps/web/          Next.js — dashboard, findings, Phase 1 flow
packages/shared-types/
data/              synthetic claims, payer-rules, evaluation splits
docs/              challenge brief, ingestion data-flow (public)
```

Root **`npm run dev`** starts API (4001) and web (4000). Python dependencies are **not** npm workspaces — install `apps/api/requirements.txt` separately.

Do not commit `apps/api/.env`, `outputs/`, or real patient data.

## License / data

Use only **synthetic** claim data in this repository unless Velodoc provides explicit datasets and sharing rules.

# ClaimGuard AI

Human-supervised agentic copilot for **healthcare claim pre-validation** (CSTAM-VELODOC, Velodoc Amazit).

The system ingests **synthetic** claim packages, normalizes them to a teaching envelope, runs payer rules **R001-R015**, produces structured explanations and corrective actions, routes ambiguous cases to human reviewers, and records a **hash-chained audit log**. Optional **Ollama** powers plain-language analysis on the JWT findings dashboard.

**Stack:** FastAPI (`apps/api`), Next.js (`apps/web`), shared types (`packages/shared-types`), PostgreSQL with pgvector for dashboard and AI storage.

Further reading: [PROJECT_REFERENCE.md](PROJECT_REFERENCE.md) | [Challenge brief](docs/challenge/CSTAM_VELODOC_BRIEF.md) | [Jury demo walkthrough](docs/SHOWCASE.md)

---

## What is in the web app

| Page | URL | Purpose |
|------|-----|---------|
| Validate claim | http://localhost:4000 | Ingest, envelope review, R001-R015, WebSocket streaming, HITL, per-claim audit panel |
| Audit and export | http://localhost:4000/audit | Global chain verify, human override export (JSON/CSV) |
| Benchmark metrics | http://localhost:4000/evaluation | Phase 2 splits (F1, latency, per-rule stats) |
| AI findings (demo) | http://localhost:4000/findings | JWT login, seeded findings, **Run AI explain** (Ollama) |
| Architecture docs | http://localhost:4000/guides | Links to markdown documentation |

The browser calls the API through **`/api`** (Next.js proxy to port **4001**). Do not point `NEXT_PUBLIC_API_URL` at the wrong port; leave it unset in `apps/web/.env.local` when possible.

---

## Prerequisites

- Node.js 18+ and npm 10+
- Python 3.11+
- Docker or Podman (PostgreSQL; required for `/findings`, JWT login, and seed data)
- Optional: [Ollama](https://ollama.com) for live LLM explanations

**Ports:** web **4000**, API **4001**, Postgres **5433** (see `docker-compose.yml`).

---

## Installation

Run from the **repository root**.

### 1. Node and Python

```bash
npm install
```

```bash
cd apps/api
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
source .venv/bin/activate
cp .env.example .env
pip install -r requirements.txt
```

Edit **`apps/api/.env`**: set **`CLAIMGUARD_JWT_SECRET`** to at least **32 characters**. Defaults for local dev are in `.env.example` (`API_KEY`, `REVIEWER_KEYS`, `DATABASE_URL`, `OLLAMA_*`).

### 2. PostgreSQL (dashboard + demo user)

From the repo root:

```bash
docker compose up -d
```

Then:

```bash
cd apps/api
python scripts/apply_migrations.py
python scripts/seed.py
cd ../..
```

Seed creates demo findings and user **`demo`** / **`claimguard-demo!`** (analyst). Check **`http://127.0.0.1:4001/health`**: `jwt_configured` should be `true` when the secret is loaded.

**Note:** Ingest and validation (**R001-R015**) work **without** Postgres. Postgres is required for `/findings`, JWT sign-in, and stored AI analysis.

**Windows bind errors on 5433:** stop the conflicting service or change the host port in `docker-compose.yml` and `DATABASE_URL`. After changing the DB image, recreate the volume once: `docker compose down -v && docker compose up -d`.

### 3. Web environment

```bash
copy apps\web\.env.example apps\web\.env.local
```

(on macOS/Linux: `cp apps/web/.env.example apps/web/.env.local`)

Set **`NEXT_PUBLIC_REVIEWER_API_KEY=reviewer-dev-key`** so HITL override buttons work (must match **`REVIEWER_KEYS`** on the API).

### 4. Start development

```bash
npm run dev
```

This starts the API and web together. API only: **`npm run dev:api`**.

---

## Service URLs

| Service | URL |
|---------|-----|
| Web UI | http://localhost:4000 |
| API root | http://127.0.0.1:4001 |
| OpenAPI | http://localhost:4001/docs |
| Health (incl. JWT diagnostics) | http://127.0.0.1:4001/health |

API requests use header **`x-api-key: dev-local-key`** unless you change **`API_KEY`** in `apps/api/.env`.

---





## Ingest formats

| Upload | Format |
|--------|--------|
| **`claims.jsonl`** | One teaching envelope per line (recommended for demos) |
| **`fhir_bundles.jsonl`** | Pack FHIR bundles |
| **`.zip`** | All five pack CSVs: `claims.csv`, `coverage.csv`, `lines.csv`, `authorizations.csv`, `attachments.csv` (see `data/evaluation/development/csv/`) |
| **`.json`** | Single pack envelope or FHIR Bundle |
| **Legacy wide `.csv`** | e.g. `data/synthetic-claims/csv/valid_sample.csv` (not pack `claims.csv`) |

Do **not** upload pack **`claims.csv` alone**. Zip the full **`csv/`** folder or use **JSONL**.

Sample data: **`data/evaluation/development/`** (claims, expected results, CSV, FHIR). Rules: **`data/payer-rules/`**.

---

## Optional: Ollama (AI explain on `/findings`)

1. Install and run Ollama.
2. Pull models matching **`apps/api/.env`** (e.g. chat model + **`nomic-embed-text`** for embeddings).
3. Restart **`npm run dev`**.

If Ollama is off, validation, audit, and benchmark still work; **Run AI explain** will fail until Ollama is available.

---

## API reference (short)

| Action | Method | Path |
|--------|--------|------|
| Ingest | POST | `/claims/ingest` (multipart `file`) |
| Validate | POST | `/v1/validate` body `{ "claim": <envelope> }` |
| Stream rules | WebSocket | `/v1/ws/validate?api_key=…` |
| Audit trace | GET | `/v1/audit/trace?claim_id=` |
| Audit verify | GET | `/v1/audit/verify` |
| Human feedback export | GET | `/v1/audit/feedback` |
| HITL route | POST | `/v1/reviews/route` |
| HITL decision | POST | `/v1/reviews/decisions` (reviewer key) |
| Rule catalog | GET | `/v1/rules` |
| JWT token | POST | `/auth/token` |
| Finding analysis | POST | `/analysis/findings/{id}` |

---

## Phase 2 deliverables

| Topic | Location |
|-------|----------|
| Evaluation report | `docs/evaluation/EVALUATION_REPORT.md` |
| Privacy and security | `docs/security/PRIVACY_AND_SECURITY.md` |
| Validation split | `data/evaluation/validation/` |

Regenerate metrics:

```bash
python scripts/materialize_validation_split.py
cd apps/api
python scripts/make_eval_report.py
```

---

## Bonus features (implemented)

These align with the CSTAM bonus list where applicable:

- **Hash-chained audit log** with verify API and UI export of human overrides (active learning dataset, not auto-retrain).
- **WebSocket** validation stream on the validate page.
- **JWT dashboard** and **Ollama** explanations on seeded findings (administrative guards, no clinical advice).

Not implemented: PDF/OCR clinical notes, dynamic payer-rule editor GUI, full automated retraining pipeline.

---

## Tests

```bash
cd apps/api
.venv\Scripts\activate
python -m pytest tests/ -q
```

(macOS/Linux: `source .venv/bin/activate`)

---

## Repository layout

```
apps/api/          FastAPI: ingest, rule engine, validation, audit, JWT, analysis
apps/web/          Next.js: validate flow, audit, benchmark, findings, guides
packages/shared-types/
data/              synthetic claims, payer rules, evaluation splits
docs/              challenge brief, showcase, evaluation, security
outputs/           local audit log (gitignored)
```

Do not commit **`apps/api/.env`**, **`apps/web/.env.local`**, **`outputs/`**, or real patient data.

---

## Data and license

Use only **synthetic** claim data in this repository unless Velodoc provides explicit datasets and sharing rules.

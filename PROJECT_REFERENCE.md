# ClaimGuard AI — Project Reference

> **Purpose:** Context for teammates working on CSTAM-VELODOC (Velodoc). Use this file as the single source of truth for structure and conventions.  
> Challenge details: `docs/challenge/CSTAM_VELODOC_BRIEF.md` · Folder guide: `docs/FOLDER_STRUCTURE.md`

---

## 1. Project overview

**ClaimGuard AI** is a human-supervised **agentic copilot** for **pre-validation** of synthetic healthcare claim packages before payer submission.

| In scope | Out of scope |
|----------|----------------|
| Administrative completeness, consistency, duplicates, unsupported fields | Clinical diagnosis or treatment decisions |
| Rule-linked evidence and corrective actions | Replacing core payer/back-office systems |
| Audit trail of checks, scores, and human overrides | Processing real patient data in the repo |

### Architecture principle

```
Synthetic claim files (FHIR R4 / CSV)     ClaimGuard AI (this repo)
────────────────────────────────────      ───────────────────────────
Dropped in data/ or POST /claims/*   →    Normalize → Rules → Explain
Velodoc-provided rule catalogue           Persist runs, findings, audit log
Human reviewers (HITL)               ←    Escalate low confidence / high severity
```

### Core capabilities (target state)

1. **Ingest & normalize** claim packages into an internal `ClaimPackage` model.
2. **Execute rules** (10–15 fictional payer rules): deterministic first, AI assist where defined.
3. **Emit structured findings** (Claim ID, Rule ID, evidence, severity, confidence, suggested action).
4. **Record audit events** for every check, recommendation, and human decision.
5. **Reviewer UI** (Next.js) for queues, overrides, and feedback (Phase 2).
6. **Optional:** Ollama/RAG for explanations grounded in `data/payer-rules/` and `apps/api/knowledge/`.

### Current implementation status

| Area | Status |
|------|--------|
| Repo layout (npm workspaces + FastAPI + Next.js + Postgres) | **Ready** — layered API in `apps/api/ARCHITECTURE.md` |
| FHIR ingestion & claim schema | **In progress** — `apps/api/app/services/` (claims), `app/infrastructure/` (FHIR) |
| Payer rule engine & audit log | **In progress** — `apps/api/app/services/` (rules, audit) |
| UI labels (ClaimGuard branding) | **Partial** — validation UI at `/findings` (rename planned) |
| Dashboard & LLM finding analysis | **Ready** — FastAPI + Next.js shell |

---

## 2. Scoring alignment (challenge)

| Phase | Theme | Repo touchpoints |
|-------|--------|------------------|
| P1 | Ingestion & normalization (15) | `apps/api` claim ingest modules, `data/synthetic-claims/` |
| P1 | Rule engine (15) | `apps/api` rules modules, `data/payer-rules/` |
| P1 | Explainability (10) | Ollama integration in `apps/api`, `ValidationFindingDto` |
| P1 | Audit log (10) | audit modules + SQL migrations |
| P2 | Benchmark F1 (15) | `data/evaluation/benchmark/`, scripts under `scripts/` |
| P2 | HITL (10) | `apps/web` review flows, override API |
| P2 | Security (5) | `docs/security/`, API key guard, input validation, prompt guards |

Bonus features: extra Python modules inside `apps/api`, WebSocket support, rule admin UI.

---

## 3. Target validation finding (structured output)

```typescript
// Target shape — implement in packages/shared-types when refactoring
interface ValidationFindingDto {
  claimId: string;
  ruleId: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  confidence: number; // 0–1
  evidence: string;   // rule-linked, cite fields/paths
  suggestedAction: string;
  explanation?: string; // human-readable (may be LLM-generated)
}
```

The API currently exposes **`UnifiedFindingDto`**; migrate to **`ValidationFindingDto`** in `@claimguard/shared-types` as claim validation lands.

---

## 4. Data model (target)

```
PayerProject (or Tenant)
  └── ValidationRun (batch or single claim submission)
        ├── Claim (normalized)
        │     └── ClaimLine[]
        ├── ValidationFinding[]
        ├── AuditEvent[] (append-only)
        └── HumanReview? (override, feedback)
```

SQL models (`Project`, `PipelineRun`, `Finding`, …) will evolve toward the entities above via migrations.

---

## 5. REST API

Base URL (local): `http://localhost:4001`  
Header: `x-api-key: <API_KEY>` (default: `dev-local-key`)

### Claim validation (target)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/claims/ingest` | Ingest FHIR bundle or CSV reference |
| `POST` | `/claims/:id/validate` | Run rule catalogue |
| `GET` | `/claims/:id/findings` | Structured validation findings |
| `GET` | `/audit?claimId=` | Audit trail |
| `POST` | `/reviews/:findingId/override` | HITL override + feedback |

### Available today

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/dashboard/overview` | Overview metrics |
| `GET` | `/findings` | List validation findings |
| `POST` | `/analysis/findings/:id` | Per-finding LLM explanation |
| `GET` | `/health` | Liveness |

---

## 6. Ports & local development

| Service | Port |
|---------|------|
| Web UI (`apps/web`) | **4000** |
| API (`apps/api`) | **4001** |
| PostgreSQL (compose) | **5433** → container 5432 |

```bash
docker compose up -d

cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/apply_migrations.py
python scripts/seed.py
cd ../..

npm install
npm run dev
```

### npm scripts (root)

| Script | Action |
|--------|--------|
| `npm run dev` | API (4001) + web (4000) |
| `npm run dev:api` | FastAPI only |
| `npm run dev:web` | Next.js only |
| `npm run build` | Build shared-types, then production Next.js build |
| `npm run lint` | ESLint on `apps/web` |
| `npm run check-types` | `tsc` on `@claimguard/shared-types` |
| `npm run clean` | Remove `.turbo` leftovers and optional Next cache |

| URL | |
|-----|---|
| UI | http://localhost:4000 |
| API | http://localhost:4001 |

Default seeded project slug: `claimguard-demo`.

---

## 7. Environment variables

### API (`apps/api/.env`)

| Variable | Default / note |
|----------|----------------|
| `DATABASE_URL` | `postgresql://claimguard:claimguard@localhost:5433/claimguard` |
| `API_KEY` | `dev-local-key` |
| `PORT` | `4001` |
| `OLLAMA_BASE_URL` | Local or LAN Ollama for explanations |
| `OLLAMA_MODEL` | Chat model for copilot text |
| `OLLAMA_EMBED_MODEL` | Embeddings for RAG over payer docs |

### Web (`apps/web`)

| Variable | Default |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:4001` |
| `NEXT_PUBLIC_API_KEY` | `dev-local-key` |
| `NEXT_PUBLIC_PROJECT_SLUG` | `claimguard-demo` |

---

## 8. Repository structure

| Layer | Tooling |
|-------|---------|
| **Frontend** | npm **workspaces**: `apps/web` + `packages/shared-types` |
| **Backend** | **Python** in `apps/api` (outside npm workspaces) |
| **Local dev** | Root `npm run dev` → `concurrently` (uvicorn + Next.js) |
| **Build / lint** | Root scripts call `npm run … --workspace=…` (no Turborepo) |

`postinstall` builds `@claimguard/shared-types` for the web app.

```
claimguard-ai/
├── apps/
│   ├── api/               # FastAPI backend (Python)
│   └── web/               # Next.js UI (npm workspace)
├── packages/
│   └── shared-types/      # @claimguard/shared-types (npm workspace)
├── data/
├── docs/
├── scripts/
├── docker-compose.yml
├── package.json
├── PROJECT_REFERENCE.md
└── README.md
```

---

## 9. Key paths (today)

| What | Path |
|------|------|
| SQL migrations | `apps/api/db/migrations/` |
| API entry | `apps/api/app/main.py` |
| LLM analysis | `apps/api/app/services/analysis.py` |
| Ollama client | `apps/api/app/infrastructure/ollama.py` |
| Web home | `apps/web/app/page.tsx` |
| Validations page (route `/findings`) | `apps/web/app/findings/page.tsx` |
| Shared types | `packages/shared-types/src/` |

New code should prefer claim modules under `apps/api/app/services/` and `apps/api/app/infrastructure/` (see folder guide).

---

## 10. Conventions

### Do

- Use **synthetic data only** in git; document dataset provenance.
- Keep **administrative** scope — escalate clinical questions to humans, never auto-decide care.
- Log every automated check and human override to the **audit** model.
- Put DTOs in `@claimguard/shared-types`.
- Use ports **4000/4001** for web/API.

### Don't

- Commit `.env`, API keys, or real PHI/PII.
- Import FastAPI or SQLAlchemy session handling into pure domain helpers (keep layers separated).
- Bypass the audit log for automated checks or human overrides.

---

*Last updated: September 2026 — `apps/api` + `apps/web` layout, npm workspaces, no Turborepo.*

# ClaimGuard API (FastAPI)

Python backend for ClaimGuard AI: REST API, Postgres (pgvector), and optional Ollama explanations.

## Setup

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env
python scripts/apply_migrations.py
python scripts/seed.py
uvicorn app.main:app --reload --port 4001
```

From the repo root, `npm run dev` starts the API and Next.js UI together.

## Layout

```
app/
  routers/       HTTP routes
  services/      Use-case orchestration
  repositories/  Persistence
  infrastructure/  Ollama, pgvector RAG
  db/              SQLAlchemy models & session
db/migrations/     Ordered SQL migrations (Postgres)
knowledge/         Markdown chunks for RAG ingest (future)
scripts/           Migrations & seed helpers
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for dependency rules.

"""Apply db/migrations SQL (dashboard schema) then Alembic revisions (ClaimGuard tables)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

load_dotenv(API_ROOT / ".env")

from app.config import settings  # noqa: E402

MIGRATIONS_ROOT = API_ROOT / "db" / "migrations"
TRACKER = "_claimguard_sql_migrations"


def _split_sql(script: str) -> list[str]:
    """Split a migration file into executable statements (PostgreSQL)."""
    # Strip line comments; keep block structure simple for our checked-in SQL.
    lines: list[str] = []
    for line in script.splitlines():
        if line.strip().startswith("--"):
            continue
        lines.append(line)
    blob = "\n".join(lines)
    parts = re.split(r";\s*\n", blob)
    out: list[str] = []
    for part in parts:
        stmt = part.strip()
        if stmt:
            out.append(stmt)
    return out


def _ensure_tracker(conn) -> None:
    conn.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {TRACKER} (
                name TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )


def _applied(conn) -> set[str]:
    rows = conn.execute(text(f"SELECT name FROM {TRACKER}")).fetchall()
    return {r[0] for r in rows}


def _apply_sql_migrations(engine) -> None:
    folders = sorted(p for p in MIGRATIONS_ROOT.iterdir() if p.is_dir())
    with engine.begin() as conn:
        _ensure_tracker(conn)
        done = _applied(conn)
        for folder in folders:
            sql_file = folder / "migration.sql"
            if not sql_file.exists():
                continue
            name = folder.name
            if name in done:
                print(f"Skip {name} (already applied)")
                continue
            print(f"Applying {name}...")
            script = sql_file.read_text(encoding="utf-8")
            for stmt in _split_sql(script):
                try:
                    conn.execute(text(stmt))
                except ProgrammingError as e:
                    msg = str(e).lower()
                    if "already exists" in msg or "duplicate" in msg:
                        print(f"  (notice) idempotent skip: {stmt[:60]}...")
                        continue
                    raise
            conn.execute(text(f"INSERT INTO {TRACKER} (name) VALUES (:n)"), {"n": name})


def _run_alembic(database_url: str) -> None:
    env = os.environ.copy()
    env["CLAIMGUARD_DATABASE_URL"] = database_url
    print("Running alembic upgrade head...")
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(API_ROOT / "alembic.ini"), "upgrade", "head"],
        cwd=str(API_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr.rstrip(), file=sys.stderr)
        raise SystemExit(proc.returncode)


def main() -> None:
    url = settings.database_url
    host_hint = url.split("@")[-1] if "@" in url else url
    print(f"Database target: {host_hint}")

    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 15})
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        print(
            "Could not connect to Postgres.\n"
            "  1. Start the database: docker compose up -d  (from repo root)\n"
            "  2. Match apps/api/.env DATABASE_URL to docker-compose ports (default localhost:5433)\n"
            "  3. Password must match POSTGRES_PASSWORD in docker-compose (default: claimguard)",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    _apply_sql_migrations(engine)
    _run_alembic(url)
    print("Migrations applied.")


if __name__ == "__main__":
    main()

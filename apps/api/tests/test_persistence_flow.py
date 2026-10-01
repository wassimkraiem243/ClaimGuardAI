import pathlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.infrastructure.audit.postgres_audit import PostgresAuditLog, get_engine
from app.infrastructure.repositories.postgres_claims import PostgresClaimRepository
import app.routers.claims as claims_router

SAMPLE = pathlib.Path(__file__).resolve().parents[3] / "data" / "synthetic-claims" / "csv" / "valid_sample.csv"
AUDIT_TABLE = "audit_events_it"


def variant(a="C001", b="C002", amount="120.5"):
    raw = SAMPLE.read_text(encoding="utf-8")
    for old, new in (("C001", a), ("C002", b), ("P001", "T-P001"), ("P002", "T-P002"), ("120.5", amount)):
        raw = raw.replace(old, new)
    return raw.encode("utf-8")


@pytest.fixture()
def client(monkeypatch):
    engine = get_engine()
    try:
        with engine.begin() as c:
            c.execute(text("DELETE FROM claims WHERE claim_id LIKE 'T-%'"))
            c.execute(text(f"DROP TABLE IF EXISTS {AUDIT_TABLE}"))
            c.execute(text(f"CREATE TABLE {AUDIT_TABLE} (LIKE audit_events INCLUDING ALL)"))
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e.__class__.__name__}")
    monkeypatch.setattr(claims_router, "get_audit_log", lambda: PostgresAuditLog(engine, AUDIT_TABLE))
    monkeypatch.setattr(claims_router, "get_claim_repository", lambda: PostgresClaimRepository(engine))
    app = FastAPI()
    app.include_router(claims_router.router)
    yield TestClient(app), engine
    with engine.begin() as c:
        c.execute(text("DELETE FROM claims WHERE claim_id LIKE 'T-%'"))
        c.execute(text(f"DROP TABLE IF EXISTS {AUDIT_TABLE}"))


def upload(c, name, data):
    return c.post("/claims/ingest-and-evaluate", files={"file": (name, data)})


def test_persistence_duplicates_and_conflict(client):
    c, engine = client
    first = upload(c, "a.csv", variant("T-001", "T-002"))
    assert first.status_code == 200
    assert "R-DUP-002" not in first.json()["summary"]["by_rule"]

    again = upload(c, "a.csv", variant("T-001", "T-002"))  # identical re-upload: idempotent
    assert again.status_code == 200
    with engine.connect() as conn:
        n = conn.execute(text("SELECT count(*) FROM claims WHERE claim_id LIKE 'T-0%'")).scalar()
    assert n == 2

    shifted = upload(c, "b.csv", variant("T-101", "T-102"))  # same services, new claim ids
    assert shifted.status_code == 200
    dups = [f for f in shifted.json()["findings"] if f["rule_id"] == "R-DUP-002"]
    assert len(dups) == 3 and any("T-001" in f["evidence"] for f in dups)

    clash = upload(c, "c.csv", variant("T-001", "T-002", amount="999"))  # same id, different content
    assert clash.status_code == 409
    assert clash.json()["detail"]["event"] == "CLAIM_CONFLICT"

    assert PostgresAuditLog(engine, AUDIT_TABLE).verify()[0] is True
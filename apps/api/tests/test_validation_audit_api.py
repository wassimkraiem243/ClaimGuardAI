import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

ROOT = Path(__file__).resolve().parents[3]
DEV_CLAIMS = ROOT / "data" / "evaluation" / "development" / "claims.jsonl"
HEADERS = {"x-api-key": "dev-local-key"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audit_log_path", str(tmp_path / "audit.jsonl"))
    monkeypatch.setattr(settings, "audit_enabled", True)
    return TestClient(app)


def test_audit_verify_and_trace(client):
    if not DEV_CLAIMS.exists():
        pytest.skip("development claims missing")
    claim = json.loads(DEV_CLAIMS.read_text(encoding="utf-8").splitlines()[0])
    r = client.post("/v1/validate", json={"claim": claim}, headers=HEADERS)
    assert r.status_code == 200
    cid = r.json()["claim_id"]
    verify = client.get("/v1/audit/verify", headers=HEADERS)
    assert verify.status_code == 200
    assert verify.json()["valid"] is True
    trace = client.get(f"/v1/audit/trace?claim_id={cid}&fast=true", headers=HEADERS)
    assert trace.status_code == 200
    assert len(trace.json()["events"]) >= 1

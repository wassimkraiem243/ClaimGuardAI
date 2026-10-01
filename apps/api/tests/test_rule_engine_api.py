import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[3]
DEV_CLAIMS = ROOT / "data" / "evaluation" / "development" / "claims.jsonl"
API_KEY = "dev-local-key"
HEADERS = {"x-api-key": API_KEY}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def clean_claim():
    if not DEV_CLAIMS.exists():
        pytest.skip("data/evaluation/development/claims.jsonl not found")
    with DEV_CLAIMS.open(encoding="utf-8") as f:
        first = json.loads(next(line for line in f if line.strip()))
    return json.loads(json.dumps(first))


@pytest.fixture(autouse=True)
def isolated_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_LOG", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("AUDIT_ENABLED", "1")


def test_validate_returns_15_results_and_run_metadata(client, clean_claim):
    r = client.post("/v1/validate", json={"claim": clean_claim}, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert len(body["results"]) == 15
    assert len(body["run"]["input_hash"]) == 64
    assert body["run"]["policy_id"] == clean_claim["policy_id"]


def test_malformed_claim_is_422(client, clean_claim):
    bad = json.loads(json.dumps(clean_claim))
    del bad["coverage"]
    r = client.post("/v1/validate", json={"claim": bad}, headers=HEADERS)
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "ingestion_error"


def test_catalog_endpoints(client):
    assert len(client.get("/v1/rules", headers=HEADERS).json()) == 15
    assert client.get("/v1/policies/EDU-PLUS", headers=HEADERS).status_code == 200

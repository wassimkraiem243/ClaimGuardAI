import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

ROOT = Path(__file__).resolve().parents[3]
DEV_CLAIMS = ROOT / "data" / "evaluation" / "development" / "claims.jsonl"
API_KEY = "dev-local-key"
HEADERS = {"x-api-key": API_KEY}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audit_log_path", str(tmp_path / "audit.jsonl"))
    monkeypatch.setattr(settings, "audit_enabled", True)
    monkeypatch.setattr(settings, "reviewer_keys", "reviewer-test-key:demo.reviewer:reviewer")
    monkeypatch.setenv("REVIEWER_KEYS", "reviewer-test-key:demo.reviewer:reviewer")
    return TestClient(app)


@pytest.fixture()
def failing_claim():
    if not DEV_CLAIMS.exists():
        pytest.skip("development claims missing")
    with DEV_CLAIMS.open(encoding="utf-8") as f:
        claim = json.loads(next(line for line in f if line.strip()))
    claim["total_amount"] = 1  # triggers R012 FAIL while keeping the envelope otherwise valid
    return claim


def test_route_puts_failures_on_queue(client, failing_claim):
    r = client.post("/v1/reviews/route", json={"claim": failing_claim}, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["escalation_required"] is True
    assert len(body["queue"]) >= 1
    assert all(item["requires_human_review"] for item in body["queue"])


def test_reviewer_decision_is_audited(client, failing_claim):
    validate = client.post("/v1/validate", json={"claim": failing_claim}, headers=HEADERS)
    assert validate.status_code == 200
    row = next(x for x in validate.json()["results"] if x["status"] == "FAIL")
    decision = client.post(
        "/v1/reviews/decisions",
        headers={**HEADERS, "x-api-key": "reviewer-test-key"},
        json={
            "claim_id": row["claim_id"],
            "rule_id": row["rule_id"],
            "action": "confirm_issue",
            "reason": "Totals mismatch confirmed on synthetic sample.",
            "original_status": row["status"],
            "finding": row,
        },
    )
    assert decision.status_code == 200
    assert decision.json()["recorded"] is True


def test_decision_without_reviewer_key_is_401(client, failing_claim):
    validate = client.post("/v1/validate", json={"claim": failing_claim}, headers=HEADERS)
    row = next(x for x in validate.json()["results"] if x["status"] == "FAIL")
    r = client.post(
        "/v1/reviews/decisions",
        headers=HEADERS,
        json={
            "claim_id": row["claim_id"],
            "rule_id": row["rule_id"],
            "action": "confirm_issue",
            "reason": "test",
            "original_status": row["status"],
        },
    )
    assert r.status_code == 401

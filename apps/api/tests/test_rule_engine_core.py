import json
from pathlib import Path

import pytest

from app.infrastructure.rule_engine.core.engine import evaluate_claim
from app.infrastructure.rule_engine.stores.policy_store import PolicyStore

ROOT = Path(__file__).resolve().parents[3]
RULES_DIR = ROOT / "data" / "payer-rules"
DEV_CLAIMS = ROOT / "data" / "evaluation" / "development" / "claims.jsonl"


@pytest.fixture(scope="session")
def store() -> PolicyStore:
    return PolicyStore.from_dir(RULES_DIR)


@pytest.fixture(scope="session")
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


def test_evaluate_returns_fifteen_results(store, clean_claim):
    results = evaluate_claim(clean_claim, store)
    assert len(results) == 15
    assert {r.rule_id for r in results} == {f"R{i:03d}" for i in range(1, 16)}

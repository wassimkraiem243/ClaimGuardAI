import pathlib
from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("httpx")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.infrastructure.audit.jsonl_audit import JsonlAuditLog  # noqa: E402
from app.routers.claims import router  # noqa: E402

DATA = pathlib.Path(__file__).resolve().parents[3] / "data" / "synthetic-claims"
ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
URL = "/claims/ingest-and-evaluate"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAIMGUARD_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_concurrent_writers_keep_chain_valid(tmp_path):
    p = tmp_path / "a.jsonl"
    with ThreadPoolExecutor(8) as ex:  # a fresh instance per call, like the router does
        list(ex.map(lambda i: JsonlAuditLog(p).append("X", f"C{i}", {"i": i}), range(40)))
    assert JsonlAuditLog(p).verify() == (True, None)
    assert len(JsonlAuditLog(p).read()) == 40


def test_oversized_upload_is_413(client):
    r = client.post(URL, files={"file": ("big.csv", b"x" * (5 * 1024 * 1024 + 1))})
    assert r.status_code == 413


def test_finding_has_category_name_and_readable_evidence(client):
    p = DATA / "csv" / "valid_sample.csv"
    r = client.post(URL, files={"file": (p.name, p.read_bytes())})
    f = next(f for f in r.json()["findings"] if f["rule_id"] == "R-AUTH-001")
    assert f["category"] == "missing" and f["rule_name"] == "Missing prior authorization"
    assert "line_no=2" in f["evidence"]


def test_findings_sorted_worst_first(client):
    p = DATA / "csv" / "valid_sample.csv"
    sev = [f["severity"] for f in client.post(URL, files={"file": (p.name, p.read_bytes())}).json()["findings"]]
    assert sev == sorted(sev, key=ORDER.get)
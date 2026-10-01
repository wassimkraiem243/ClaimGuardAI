import pathlib
import pytest

pytest.importorskip("httpx")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.routers.claims import router  # noqa: E402

DATA = pathlib.Path(__file__).resolve().parents[3] / "data" / "synthetic-claims"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAIMGUARD_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def post(client, rel, url="/claims/ingest-and-evaluate"):
    p = DATA / rel
    return client.post(url, files={"file": (p.name, p.read_bytes())})


def test_csv_flags_missing_authorization(client):
    r = post(client, "csv/valid_sample.csv")
    assert r.status_code == 200
    hits = {(f["claim_id"], f["rule_id"], f["line_no"]) for f in r.json()["findings"]}
    assert ("C001", "R-AUTH-001", 2) in hits
    assert r.json()["summary"]["claims"] == 2


def test_fhir_clean_bundle_has_no_findings(client):
    r = post(client, "fhir/valid_bundle.json")
    assert r.status_code == 200 and r.json()["findings"] == []


def test_rejection_is_audited_and_chain_verifies(client):
    assert post(client, "fhir/broken_bundle.json").status_code == 400
    events = client.get("/claims/audit").json()
    print(r.status_code, r.text)
    assert [e["type"] for e in events] == ["INGESTION_REJECTED"]
    assert client.get("/claims/audit/verify").json()["valid"] is True


def test_unsupported_type_is_415(client):
    r = client.post("/claims/ingest-and-evaluate", files={"file": ("x.txt", b"hi")})
    assert r.status_code == 415
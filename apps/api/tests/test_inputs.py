import csv
import io
import pathlib
import re
from types import SimpleNamespace

import pytest

pytest.importorskip("httpx")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.infrastructure.parsers.preflight import (InputRejected, check_fhir, prepare_csv,  # noqa: E402
                                                   reject_duplicate_ids)
from app.routers.claims import router  # noqa: E402

DATA = pathlib.Path(__file__).resolve().parents[3] / "data" / "synthetic-claims"
URL = "/claims/ingest-and-evaluate"
ORIGINAL = (DATA / "csv" / "valid_sample.csv").read_bytes()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAIMGUARD_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def variant(delimiter, decimal_comma=False):
    rows = list(csv.reader(io.StringIO(ORIGINAL.decode("utf-8-sig"))))
    out = io.StringIO()
    w = csv.writer(out, delimiter=delimiter, lineterminator="\r\n")
    for r in rows:
        w.writerow([c.replace(".", ",") if decimal_comma and re.fullmatch(r"-?\d+\.\d+", c) else c for c in r])
    return out.getvalue().encode("utf-8")


def post(client, name, data):
    return client.post(URL, files={"file": (name, data)})


def test_messy_csv_variants_parse_identically(client):
    baseline = post(client, "a.csv", ORIGINAL).json()["claims"]
    variants = {
        "semicolon": variant(";"),
        "semicolon + decimal comma (French Excel)": variant(";", decimal_comma=True),
        "tab": variant("\t"),
        "utf-8 BOM": b"\xef\xbb\xbf" + ORIGINAL,
        "blank lines": ORIGINAL + b"\n\n\n",
    }
    for label, data in variants.items():
        r = post(client, "v.csv", data)
        assert r.status_code == 200, label
        assert r.json()["claims"] == baseline, label


@pytest.mark.parametrize("name,data,needle", [
    ("e.csv", b"", "Empty"),
    ("h.csv", b"claim_id,amount\n", "no data rows"),
    ("b.json", b"{ not json", "Invalid JSON"),
    ("n.json", b'{"hello": 1}', "Expected a FHIR Bundle"),
    ("c.json", b'{"resourceType":"Bundle","entry":[]}', "no Claim"),
])
def test_bad_inputs_are_clean_400s(client, name, data, needle):
    r = post(client, name, data)
    assert r.status_code == 400
    d = r.json()["detail"]
    assert d["event"] == "INGESTION_REJECTED" and needle in d["reason"]


def test_envelope_is_versioned_and_pretty(client):
    r = post(client, "a.csv", ORIGINAL)
    body = r.json()
    assert body["schema_version"] == "1.0"
    assert len(body["meta"]["sha256"]) == 64 and body["meta"]["format"] == "CSV"
    s = body["summary"]
    assert s["claims"] == s["claims_with_findings"] + s["claims_clean"]
    assert "by_category" in s and "by_rule" in s
    assert r.text.startswith("{\n  ")  # indented


def test_decimal_comma_untouched_in_comma_files():
    out = prepare_csv(b"a,b\n1,2\n").decode()
    assert out == "a,b\n1,2\n"


def test_duplicate_claim_ids_rejected():
    reject_duplicate_ids([SimpleNamespace(claim_id="A"), SimpleNamespace(claim_id="B")])
    with pytest.raises(InputRejected):
        reject_duplicate_ids([SimpleNamespace(claim_id="A"), SimpleNamespace(claim_id="A")])


def test_fhir_bom_is_stripped():
    raw = b'\xef\xbb\xbf{"resourceType":"Bundle","entry":[{"resource":{"resourceType":"Claim"}}]}'
    assert check_fhir(raw).startswith(b"{")
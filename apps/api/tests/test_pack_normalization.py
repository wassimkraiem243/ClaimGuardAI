import io
import json
import pathlib
import zipfile

import pytest

from app.domain.claim_package import IngestionRejected
from app.infrastructure.parsers.jsonl_parser import JsonlEnvelopeParser
from app.infrastructure.parsers.pack_csv_zip_parser import PackCsvZipParser
from app.infrastructure.parsers.pack_fhir_parser import PackFhirBundleParser
from app.services.rule_validation import get_policy_store, validate_envelope

ROOT = pathlib.Path(__file__).resolve().parents[3]
DEV = ROOT / "data" / "evaluation" / "development"
PACK = ROOT / "ClaimGuardAI_Student_Starter_Pack" / "data" / "development"


def _zip_csv_folder(folder: pathlib.Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name in ("claims.csv", "coverage.csv", "lines.csv", "authorizations.csv", "attachments.csv"):
            path = folder / name
            zf.writestr(name, path.read_bytes())
    return buf.getvalue()


@pytest.fixture(autouse=True)
def isolated_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_LOG", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("AUDIT_ENABLED", "0")


@pytest.fixture(scope="module")
def first_envelope():
    path = DEV / "claims.jsonl"
    if not path.exists():
        pytest.skip("development claims.jsonl missing")
    line = path.read_text(encoding="utf-8").splitlines()[0]
    return json.loads(line)


def test_jsonl_first_line_matches_transport(first_envelope):
    (norm,) = JsonlEnvelopeParser().parse((json.dumps(first_envelope) + "\n").encode())
    assert norm.source == "JSONL"
    assert norm.envelope["claim_id"] == first_envelope["claim_id"]
    assert len(norm.envelope["lines"]) == len(first_envelope["lines"])


def test_pack_csv_zip_round_trip():
    folder = DEV / "csv"
    if not (folder / "claims.csv").exists():
        pytest.skip("development csv folder missing")
    claims = PackCsvZipParser().parse(_zip_csv_folder(folder))
    assert len(claims) >= 400
    sample = next(c for c in claims if c.envelope["claim_id"] == "CG-27BFD8541DEB")
    assert sample.source == "PACK_CSV"
    assert sample.envelope["policy_id"] == "EDU-PLUS"
    assert len(sample.envelope["lines"]) == 2


def test_pack_fhir_simple_bundle_matches_jsonl(first_envelope):
    bundles = DEV / "fhir_bundles.jsonl"
    if not bundles.exists():
        pytest.skip("fhir_bundles.jsonl missing")
    line = bundles.read_text(encoding="utf-8").splitlines()[0]
    (norm,) = PackFhirBundleParser().parse(line.encode())
    assert norm.source == "FHIR_PACK"
    assert norm.envelope["claim_id"] == first_envelope["claim_id"]
    assert norm.envelope["total_amount"] == first_envelope["total_amount"]
    assert [l["line_id"] for l in norm.envelope["lines"]] == [
        l["line_id"] for l in first_envelope["lines"]
    ]


def test_ingested_envelope_runs_rule_engine(first_envelope):
    (norm,) = JsonlEnvelopeParser().parse((json.dumps(first_envelope) + "\n").encode())
    resp = validate_envelope(norm.envelope)
    assert len(resp.results) == 15


@pytest.mark.parametrize("path", [PACK / "claims.jsonl", DEV / "claims.jsonl"])
def test_jsonl_file_ingest(path):
    if not path.exists():
        pytest.skip(f"{path} not found")
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    claims = JsonlEnvelopeParser().parse((first_line + "\n").encode())
    assert claims[0].envelope["schema_version"] == "1.0.0"


def test_bad_jsonl_rejected():
    with pytest.raises(IngestionRejected):
        JsonlEnvelopeParser().parse(b'{"claim_id":"X"}\n')

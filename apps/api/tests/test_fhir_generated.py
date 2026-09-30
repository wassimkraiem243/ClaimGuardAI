"""Runs every generated bundle and compares the outcome to manifest.json."""
import json
import pathlib
import pytest
from app.domain.claim_package import IngestionRejected
from app.infrastructure.parsers.fhir_parser import FhirClaimParser

G = pathlib.Path(__file__).resolve().parents[3] / "data" / "synthetic-claims" / "fhir" / "generated"
MANIFEST = json.loads((G / "manifest.json").read_text()) if (G / "manifest.json").exists() else {}
parser = FhirClaimParser()


@pytest.mark.skipif(not MANIFEST, reason="run scripts/generate_fhir_samples.py first")
@pytest.mark.parametrize("name", sorted(MANIFEST))
def test_generated_bundle(name):
    exp, raw = MANIFEST[name], (G / name).read_bytes()
    if exp["expect"] == "ok":
        claims = parser.parse(raw)
        assert len(claims) == exp["claims"]
        assert all(c.lines and c.patient.id for c in claims)
    else:
        with pytest.raises(IngestionRejected) as e:
            parser.parse(raw)
        if "field_path" in exp:
            assert e.value.field_path == exp["field_path"]


def test_special_cases():
    by = lambda n: parser.parse((G / n).read_bytes())  # noqa: E731
    (c,) = by("v06_principal_servicedperiod.json")
    assert [d.code for d in c.diagnoses if d.primary] == ["J45.0"]
    assert c.lines[0].service_date == "2026-06-10"
    (m,) = by("v05_minimal_optional.json")
    assert {"patient gender missing", "provider npi missing", "payer_id missing", "no diagnosis codes"} <= set(m.ingestion_warnings)
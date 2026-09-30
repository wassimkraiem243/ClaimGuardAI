import json
import pathlib
import pytest
from app.domain.claim_package import IngestionRejected
from app.infrastructure.parsers.fhir_parser import FhirClaimParser

D = pathlib.Path(__file__).resolve().parents[3] / "data" / "synthetic-claims" / "fhir"
parser = FhirClaimParser()


def test_valid_bundle_normalizes():
    (c,) = parser.parse((D / "valid_bundle.json").read_bytes())
    assert c.claim_id == "F001" and c.source == "FHIR"
    assert c.patient.gender == "F" and c.patient.birth_date == "1985-03-12"
    assert c.encounter.start == "2026-05-02" and c.coverage.policy_id == "POL-77"
    assert c.coverage.payer_id == "PAYER-A" and c.provider.npi == "1234567890"
    assert [d.code for d in c.diagnoses] == ["J45.0", "R05"] and c.diagnoses[0].primary
    assert len(c.lines) == 2 and c.lines[0].amount == 120.5 and c.lines[0].authorization_id == "AUTH-1"


def test_dangling_reference_rejected():
    with pytest.raises(IngestionRejected) as e:
        parser.parse((D / "broken_bundle.json").read_bytes())
    assert e.value.field_path == "Claim.patient" and e.value.claim_id == "F001"


@pytest.mark.parametrize("raw", [b"not json", b"[]", b'{"resourceType":"Patient"}',
                                 b'{"resourceType":"Bundle","entry":[]}', b"\xff\xfe\x00"])
def test_malformed_input_rejected(raw):
    with pytest.raises(IngestionRejected):
        parser.parse(raw)


def test_wrong_types_rejected_not_crashed():
    b = json.loads((D / "valid_bundle.json").read_bytes())
    claim = next(e["resource"] for e in b["entry"] if e["resource"]["resourceType"] == "Claim")
    claim["item"][0]["net"] = "120.5"
    with pytest.raises(IngestionRejected):
        parser.parse(json.dumps(b).encode())
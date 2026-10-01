import json
import pathlib
import pytest
from app.domain.claim_package import IngestionRejected
from app.infrastructure.parsers.fhir_parser import FhirClaimParser

D = pathlib.Path(__file__).resolve().parents[3] / "data" / "synthetic-claims" / "fhir"
parser = FhirClaimParser()


def test_valid_bundle_normalizes():
    (norm,) = parser.parse_normalized((D / "valid_bundle.json").read_bytes())
    env = norm.envelope
    assert env["claim_id"] == "F001" and norm.source == "FHIR_LEGACY"
    assert env["patient_id"] == "P001"
    assert env["lines"][0]["net_amount"] == 120.5


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
import copy
import json

import pytest
from app.domain.claim_package import IngestionRejected
from app.infrastructure.parsers.fhir_parser import FhirClaimParser
from app.infrastructure.parsers.preflight import InputRejected, check_fhir

parser = FhirClaimParser()


def bundle():
    return {"resourceType": "Bundle", "type": "collection", "entry": [
        {"resource": {"resourceType": "Patient", "id": "P001", "gender": "female", "birthDate": "1985-03-12"}},
        {"resource": {"resourceType": "Practitioner", "id": "PRV-9",
                      "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": "1234567890"}]}},
        {"resource": {"resourceType": "Coverage", "id": "COV1", "identifier": [{"value": "POL-77"}],
                      "payor": [{"reference": "Organization/PAYER-A"}],
                      "period": {"start": "2026-01-01", "end": "2026-12-31"}}},
        {"resource": {"resourceType": "Encounter", "id": "E001", "period": {"start": "2026-05-02", "end": "2026-05-02"}}},
        {"resource": {"resourceType": "Encounter", "id": "E002", "period": {"start": "2026-05-09", "end": "2026-05-09"}}},
        {"resource": {"resourceType": "Claim", "id": "F001", "use": "claim",
                      "patient": {"reference": "Patient/P001"}, "provider": {"reference": "Practitioner/PRV-9"},
                      "insurance": [{"sequence": 1, "focal": True, "coverage": {"reference": "Coverage/COV1"},
                                     "preAuthRef": ["AUTH-1"]}],
                      "diagnosis": [{"sequence": 1, "diagnosisCodeableConcept": {"coding": [{"code": "j45.0"}]}}],
                      "item": [{"sequence": n, "productOrService": {"coding": [{"code": code}]},
                                "quantity": {"value": 1}, "net": {"value": amt, "currency": "USD"},
                                "servicedDate": "2026-05-02", "encounter": [{"reference": "Encounter/E001"}]}
                               for n, code, amt in ((1, "99213", 120.5), (2, "94010", 80))]}}]}


def claim(b):
    return b["entry"][5]["resource"]


def parse(b):
    return parser.parse(json.dumps(b).encode())


def test_clean_bundle_has_no_warnings():
    c = parse(bundle())[0]
    assert c.ingestion_warnings == [] and [l.amount for l in c.lines] == [120.5, 80.0]


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_non_finite_amounts_rejected(token):
    raw = json.dumps(bundle()).replace('"value": 120.5', f'"value": {token}').encode()
    with pytest.raises(IngestionRejected) as e:
        parser.parse(raw)
    assert "finite" in e.value.reason.lower()


def test_deeply_nested_json_is_a_clean_rejection_not_a_crash():
    with pytest.raises(IngestionRejected):
        parser.parse(b"[" * 200000)
    with pytest.raises(InputRejected):
        check_fhir(b"[" * 200000)


def test_items_with_different_encounters_warn():
    b = bundle()
    claim(b)["item"][1]["encounter"] = [{"reference": "Encounter/E002"}]
    c = parse(b)[0]
    assert c.encounter.id == "E001"
    assert "items reference several encounters; using the first" in c.ingestion_warnings


def test_dangling_encounter_on_a_later_item_is_rejected():
    b = bundle()
    claim(b)["item"][1]["encounter"] = [{"reference": "Encounter/NOPE"}]
    with pytest.raises(IngestionRejected) as e:
        parse(b)
    assert "Encounter/NOPE" in e.value.reason and e.value.claim_id == "F001"


def test_missing_serviced_date_is_a_warning():
    b = bundle()
    del claim(b)["item"][0]["servicedDate"]
    assert "line 1: service_date missing" in parse(b)[0].ingestion_warnings


def test_non_claim_use_is_flagged():
    b = bundle()
    claim(b)["use"] = "preauthorization"
    assert any("preauthorization" in w for w in parse(b)[0].ingestion_warnings)


def test_datetime_service_dates_keep_the_date_part():
    b = bundle()
    claim(b)["item"][0]["servicedDate"] = "2026-05-02T10:30:00Z"
    assert parse(b)[0].lines[0].service_date == "2026-05-02"

def test_malformed_structure_keeps_the_claim_id():
    b = bundle()
    claim(b)["item"].append(5)  # an item that is not an object
    with pytest.raises(IngestionRejected) as e:
        parse(b)
    assert e.value.claim_id == "F001" and "Malformed" in e.value.reason

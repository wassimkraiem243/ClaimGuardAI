import pathlib
import pytest
from app.domain.claim_package import IngestionRejected
from app.infrastructure.parsers.csv_parser import CsvClaimParser

# tests/ -> api/ -> apps/ -> repo root
D = pathlib.Path(__file__).resolve().parents[3] / "data" / "synthetic-claims" / "csv"
parser = CsvClaimParser()


def test_valid_sample_normalizes():
    claims = parser.parse_normalized((D / "valid_sample.csv").read_bytes())
    assert [c.envelope["claim_id"] for c in claims] == ["C001", "C002"]
    c1 = claims[0].envelope
    assert len(c1["lines"]) == 2 and c1["diagnosis_code"] == "J45.0"
    assert claims[0].source == "CSV_LEGACY"
    assert any("legacy flat CSV" in w for w in claims[0].ingestion_warnings)


def test_broken_rejected_with_field_path():
    with pytest.raises(IngestionRejected) as e:
        parser.parse((D / "broken_sample.csv").read_bytes())
    assert e.value.claim_id == "C900"


def test_missing_columns_rejected():
    with pytest.raises(IngestionRejected):
        parser.parse(b"claim_id,patient_id\nC1,P1\n")


def test_inconsistent_patient_rejected():
    hdr = "claim_id,patient_id,encounter_id,policy_id,provider_id,line_no,procedure_code,quantity,amount\n"
    with pytest.raises(IngestionRejected):
        parser.parse((hdr + "C1,P1,E1,POL,PRV,1,99213,1,10\nC1,P2,E1,POL,PRV,2,99213,1,10\n").encode())


def test_empty_and_binary_rejected():
    with pytest.raises(IngestionRejected):
        parser.parse(b"")
    with pytest.raises(IngestionRejected):
        parser.parse(b"\xff\xfe\x00\x00")
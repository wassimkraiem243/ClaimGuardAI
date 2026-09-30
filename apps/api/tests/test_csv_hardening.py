import pytest
from app.domain.claim_package import IngestionRejected
from app.infrastructure.parsers.csv_parser import CsvClaimParser
from app.mappers.normalizer import norm_date, norm_number

H = ("claim_id,patient_id,encounter_id,policy_id,provider_id,line_no,procedure_code,quantity,amount,"
     "birth_date,coverage_end,diagnosis_codes\n")
parser = CsvClaimParser()


def parse(*rows):
    return parser.parse((H + "\n".join(rows) + "\n").encode())


@pytest.mark.parametrize("raw,expected", [
    ("1200.50", 1200.5), ("1200,50", 1200.5), ("1 200,50", 1200.5), ("1\u00a0200,50", 1200.5),
    ("1,200.50", 1200.5), ("1.200,50", 1200.5), ("1,200,000", 1200000.0), ("-5", -5.0), ("0", 0.0),
])
def test_norm_number_accepts(raw, expected):
    assert norm_number(raw) == expected


@pytest.mark.parametrize("raw", ["nan", "NaN", "inf", "-inf", "Infinity", "1e3", "abc", "", "1.2.3", "--5"])
def test_norm_number_rejects(raw):
    with pytest.raises(ValueError):
        norm_number(raw)


def test_nan_and_inf_never_reach_the_rules():
    for bad in ("nan", "inf"):
        with pytest.raises(IngestionRejected) as e:
            parse(f"C1,P1,E1,POL,PRV,1,99213,1,{bad},,,")
        assert e.value.field_path == "row 2.amount" and e.value.claim_id == "C1"


def test_quantity_error_names_the_column():
    with pytest.raises(IngestionRejected) as e:
        parse("C1,P1,E1,POL,PRV,1,99213,x,10,,,")
    assert e.value.field_path == "row 2.quantity"


def test_blank_first_row_does_not_hide_later_values():
    c = parse("C1,P1,E1,POL,PRV,1,99213,1,10,,,", "C1,P1,E1,POL,PRV,2,99213,1,10,1980-01-01,2026-12-31,j45.0;r05")[0]
    assert c.patient.birth_date == "1980-01-01" and c.coverage.end == "2026-12-31"
    assert [d.code for d in c.diagnoses] == ["J45.0", "R05"]
    assert "birth_date missing" not in c.ingestion_warnings


def test_same_date_in_two_formats_is_not_a_conflict():
    c = parse("C1,P1,E1,POL,PRV,1,99213,1,10,1980-07-14,,", "C1,P1,E1,POL,PRV,2,99213,1,10,14/07/1980,,")[0]
    assert c.patient.birth_date == "1980-07-14"


@pytest.mark.parametrize("a,b,col", [
    ("1980-01-01", "1999-09-09", "birth_date"),
    ("2026-12-31", "2026-06-30", "coverage_end"),
    ("j45.0", "i10", "diagnosis_codes"),
])
def test_conflicting_claim_level_values_rejected(a, b, col):
    def row(n, v):
        bd = v if col == "birth_date" else ""
        ce = v if col == "coverage_end" else ""
        dx = v if col == "diagnosis_codes" else ""
        return f"C1,P1,E1,POL,PRV,{n},99213,1,10,{bd},{ce},{dx}"
    with pytest.raises(IngestionRejected) as e:
        parse(row(1, a), row(2, b))
    assert e.value.field_path == col and "Conflicting" in e.value.reason


def test_identity_fields_stay_strict_when_one_row_is_blank():
    with pytest.raises(IngestionRejected):
        parse("C1,P1,E1,POL,PRV,1,99213,1,10,,,", "C1,,E1,POL,PRV,2,99213,1,10,,,")


def test_missing_service_date_is_a_warning():
    c = parse("C1,P1,E1,POL,PRV,1,99213,1,10,,,")[0]
    assert "line 1: service_date missing" in c.ingestion_warnings


def test_line_no_must_be_positive_integer():
    for bad in ("0", "-1", "1.5", "x"):
        with pytest.raises(IngestionRejected):
            parse(f"C1,P1,E1,POL,PRV,{bad},99213,1,10,,,")


def test_iso_datetime_and_dotted_dates():
    assert norm_date("2026-05-02T10:30:00") == "2026-05-02"
    assert norm_date("02.05.2026") == "2026-05-02"
    assert norm_date("02/06/2026") == "2026-06-02"  # day-first, by design
    with pytest.raises(ValueError):
        norm_date("2026-13-45")
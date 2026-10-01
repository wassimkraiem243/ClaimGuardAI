import pytest
from sqlalchemy import text

from app.domain.claim_package import (ClaimLine, ClaimPackage, Coverage, Diagnosis, Encounter, Patient, Provider)
from app.domain.claim_repository import ClaimConflict
from app.domain.rules import BatchContext, dup_002
from app.infrastructure.audit.postgres_audit import get_engine
from app.infrastructure.repositories.postgres_claims import PostgresClaimRepository


def claim(cid, patient="T-P1", amount=100.0):
    return ClaimPackage(
        claim_id=cid, source="CSV", patient=Patient(id=patient, birth_date="1980-01-01", gender="F"),
        encounter=Encounter(id="E1", start="2026-05-02", end="2026-05-02"),
        coverage=Coverage(policy_id="POL", payer_id="PAYER-A", start="2026-01-01", end="2026-12-31"),
        provider=Provider(id="PRV", npi="1234567890"), diagnoses=[Diagnosis(code="J45.0", primary=True)],
        lines=[ClaimLine(line_no=1, procedure_code="99213", quantity=1, amount=amount, currency="USD",
                         service_date="2026-05-02", authorization_id="AUTH-1")])


@pytest.fixture()
def repo():
    engine = get_engine()
    try:
        with engine.begin() as c:
            c.execute(text("DELETE FROM claims WHERE claim_id LIKE 'T-%'"))
    except Exception as e:
        pytest.skip(f"PostgreSQL not available (or migration 0002 not applied): {e.__class__.__name__}")
    yield PostgresClaimRepository(engine)
    with engine.begin() as c:
        c.execute(text("DELETE FROM claims WHERE claim_id LIKE 'T-%'"))


def test_save_is_idempotent_for_identical_claim(repo):
    assert repo.save(claim("T-1"), "sha", "2026-10-01") is True
    assert repo.save(claim("T-1"), "sha", "2026-10-01") is False
    assert repo.get("T-1")["claim_id"] == "T-1"


def test_same_id_different_content_conflicts(repo):
    repo.save(claim("T-1"), "sha", "2026-10-01")
    with pytest.raises(ClaimConflict):
        repo.save(claim("T-1", amount=999.0), "sha2", "2026-10-02")


def test_prior_services_excludes_own_batch_and_feeds_dup_rule(repo):
    repo.save(claim("T-1"), "sha", "2026-10-01")
    second = claim("T-2")  # same patient, procedure and date, uploaded later
    known = repo.prior_services([second])
    assert known == {("T-P1", "99213", "2026-05-02"): {"T-1"}}
    hits = dup_002(second, {}, BatchContext([second], known))
    assert len(hits) == 1 and "T-1" in hits[0][0]
    assert repo.prior_services([claim("T-1")]) == {}  # own id is excluded
    assert dup_002(claim("T-3", patient="T-OTHER"), {}, BatchContext([claim("T-3", patient="T-OTHER")], known)) == []
import copy
import pytest
from app.domain.claim_package import (ClaimLine, ClaimPackage, Coverage, Diagnosis, Encounter, Patient, Provider)
from app.infrastructure.rules.catalogue import load_catalogue
from app.services.evaluate_claims import EvaluateClaims


def good(cid="C1", patient="P1"):
    return ClaimPackage(
        claim_id=cid, source="CSV", patient=Patient(id=patient, birth_date="1980-01-01", gender="F"),
        encounter=Encounter(id="E1", start="2026-05-02", end="2026-05-02"),
        coverage=Coverage(policy_id="POL", payer_id="PAYER-A", start="2026-01-01", end="2026-12-31"),
        provider=Provider(id="PRV", npi="1234567890"), diagnoses=[Diagnosis(code="J45.0", primary=True)],
        lines=[ClaimLine(line_no=1, procedure_code="99213", quantity=1, amount=100, currency="USD",
                         service_date="2026-05-02", authorization_id="AUTH-1")])


def mutate(fn):
    c = copy.deepcopy(good())
    fn(c)
    return c


CASES = {
    "R-AMT-001": lambda c: setattr(c.lines[0], "amount", 99999),
    "R-QTY-001": lambda c: setattr(c.lines[0], "quantity", 0),
    "R-COV-001": lambda c: setattr(c.coverage, "end", "2026-03-01"),
    "R-AUTH-001": lambda c: (setattr(c.lines[0], "procedure_code", "94010"), setattr(c.lines[0], "authorization_id", None)),
    "R-DUP-001": lambda c: c.lines.append(c.lines[0].model_copy(update={"line_no": 2})),
    "R-DX-001": lambda c: setattr(c, "diagnoses", []),
    "R-DX-002": lambda c: setattr(c.diagnoses[0], "code", "12345"),
    "R-PRV-001": lambda c: setattr(c.provider, "npi", "123"),
    "R-DATE-001": lambda c: setattr(c.encounter, "end", "2026-05-01"),
    "R-PAT-001": lambda c: setattr(c.patient, "birth_date", "2030-01-01"),
    "R-CUR-001": lambda c: setattr(c.lines[0], "currency", None),
}
engine = EvaluateClaims(load_catalogue())


def test_clean_claim_has_no_findings():
    assert engine.execute([good()]) == []


@pytest.mark.parametrize("rule_id", sorted(CASES))
def test_rule_fires(rule_id):
    findings = engine.execute([mutate(CASES[rule_id])])
    assert rule_id in {f.rule_id for f in findings}
    f = next(f for f in findings if f.rule_id == rule_id)
    assert f.evidence and f.suggested_action and 0 <= f.confidence <= 1


def test_duplicate_across_claims():
    a, b = good("C1"), good("C2")
    ids = {(f.claim_id, f.rule_id) for f in engine.execute([a, b])}
    assert ("C1", "R-DUP-002") in ids and ("C2", "R-DUP-002") in ids
    assert engine.execute([good("C1"), good("C2", patient="OTHER")]) == []


def test_unknown_rule_in_catalogue_fails_loudly():
    cat = load_catalogue()
    cat[0] = cat[0].model_copy(update={"id": "R-NOPE-999"})
    with pytest.raises(ValueError):
        EvaluateClaims(cat)


def test_disabled_rule_is_skipped():
    cat = [r.model_copy(update={"enabled": r.id != "R-AMT-001"}) for r in load_catalogue()]
    assert "R-AMT-001" not in {f.rule_id for f in EvaluateClaims(cat).execute([mutate(CASES["R-AMT-001"])])}
"""Rule-engine benchmark: labelled synthetic claims -> per-rule precision / recall / F1.
Run from the repo root:  python scripts\benchmark.py"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.domain.claim_package import (ClaimLine, ClaimPackage, Coverage, Diagnosis,  # noqa: E402
                                       Encounter, Patient, Provider)
from app.infrastructure.rules.catalogue import load_catalogue  # noqa: E402
from app.services.evaluate_claims import EvaluateClaims  # noqa: E402

OUT = ROOT / "data" / "evaluation" / "benchmark"


def good(cid, patient):
    return ClaimPackage(
        claim_id=cid, source="CSV", patient=Patient(id=patient, birth_date="1980-01-01", gender="F"),
        encounter=Encounter(id="E1", start="2026-05-02", end="2026-05-02"),
        coverage=Coverage(policy_id="POL", payer_id="PAYER-A", start="2026-01-01", end="2026-12-31"),
        provider=Provider(id="PRV", npi="1234567890"), diagnoses=[Diagnosis(code="J45.0", primary=True)],
        lines=[ClaimLine(line_no=1, procedure_code="99213", quantity=1, amount=100, currency="USD",
                         service_date="2026-05-02", authorization_id="AUTH-1")])


def _auth(c):
    c.lines[0].procedure_code = "94010"
    c.lines[0].authorization_id = None


def _on_date(c, d):
    c.encounter.start = c.encounter.end = c.lines[0].service_date = d


def _other_day_line(c):
    c.encounter.end = "2026-05-03"
    c.lines.append(c.lines[0].model_copy(update={"line_no": 2, "service_date": "2026-05-03"}))


# defect injectors: each must trigger exactly its own rule
POSITIVE = {
    "R-AMT-001": lambda c: setattr(c.lines[0], "amount", 99999),
    "R-QTY-001": lambda c: setattr(c.lines[0], "quantity", 0),
    "R-COV-001": lambda c: setattr(c.coverage, "end", "2026-03-01"),
    "R-AUTH-001": _auth,
    "R-DUP-001": lambda c: c.lines.append(c.lines[0].model_copy(update={"line_no": 2})),
    "R-DX-001": lambda c: setattr(c, "diagnoses", []),
    "R-DX-002": lambda c: setattr(c.diagnoses[0], "code", "12345"),
    "R-PRV-001": lambda c: setattr(c.provider, "npi", "123"),
    "R-DATE-001": lambda c: setattr(c.encounter, "end", "2026-05-01"),
    "R-PAT-001": lambda c: setattr(c.patient, "birth_date", "2030-01-01"),
    "R-CUR-001": lambda c: setattr(c.lines[0], "currency", None),
}

# hard negatives: boundary values that are VALID and must NOT raise any finding
NEGATIVE = {
    "amount_exactly_at_cap": lambda c: setattr(c.lines[0], "amount", 10000),
    "quantity_exactly_max": lambda c: setattr(c.lines[0], "quantity", 100),
    "service_on_coverage_end": lambda c: _on_date(c, "2026-12-31"),
    "service_on_coverage_start": lambda c: _on_date(c, "2026-01-01"),
    "npi_leading_zeros": lambda c: setattr(c.provider, "npi", "0000000000"),
    "icd10_without_decimal": lambda c: setattr(c.diagnoses[0], "code", "A00"),
    "icd10_long_extension": lambda c: setattr(c.diagnoses[0], "code", "Z99.89"),
    "same_procedure_other_day": _other_day_line,
    "auth_present_on_94010": lambda c: setattr(c.lines[0], "procedure_code", "94010"),
    "birth_date_on_encounter_day": lambda c: setattr(c.patient, "birth_date", "2026-05-02"),
}


def build_cases(seed, n):
    rng, cases, rules = random.Random(seed), [], sorted(POSITIVE)
    for i in range(n):  # random mixes of 0-3 injected defects
        c = good(f"B{i:03d}", f"P{i:03d}")
        picked = rng.sample(rules, rng.choice([0, 1, 1, 2, 3]))
        if "R-DX-001" in picked and "R-DX-002" in picked:  # empty diagnoses leaves nothing for DX-002 to check
            picked.remove("R-DX-002")
        for r in picked:
            POSITIVE[r](c)
        cases.append((c, set(picked)))
    for i, fn in enumerate(NEGATIVE.values()):
        c = good(f"H{i:02d}", f"PH{i:02d}")
        fn(c)
        cases.append((c, set()))
    for i in range(10):  # cross-claim duplicates: both claims must be flagged
        cases += [(good(f"X{i:02d}a", f"PX{i:02d}"), {"R-DUP-002"}), (good(f"X{i:02d}b", f"PX{i:02d}"), {"R-DUP-002"})]
    for i in range(5):  # same patient + procedure, different day: must NOT be flagged
        a, b = good(f"Y{i:02d}a", f"PY{i:02d}"), good(f"Y{i:02d}b", f"PY{i:02d}")
        _on_date(b, "2026-05-03")
        cases += [(a, set()), (b, set())]
    return cases


def ratio(num, den):
    return round(num / den, 3) if den else 1.0


def main(seed=42, n=200):
    cases = build_cases(seed, n)
    catalogue = load_catalogue()
    findings = EvaluateClaims(catalogue).execute([c for c, _ in cases])
    got = {(f.claim_id, f.rule_id) for f in findings}
    exp = {(c.claim_id, r) for c, rs in cases for r in rs}

    per_rule = {}
    for r in (x.id for x in catalogue):
        tp = len({k for k in exp & got if k[1] == r})
        fp = len({k for k in got - exp if k[1] == r})
        fn = len({k for k in exp - got if k[1] == r})
        p, rec = ratio(tp, tp + fp), ratio(tp, tp + fn)
        per_rule[r] = {"support": tp + fn, "tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": rec,
                       "f1": round(2 * p * rec / (p + rec), 3) if p + rec else 0.0}

    exact = sum(1 for c, rs in cases if {r for (cid, r) in got if cid == c.claim_id} == rs)
    result = {"seed": seed, "claims": len(cases), "claims_exact_match": exact,
              "exact_match_rate": ratio(exact, len(cases)), "per_rule": per_rule,
              "false_positives": sorted(map(list, got - exp)), "false_negatives": sorted(map(list, exp - got))}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [f"# Rule-engine benchmark (seed {seed}, {len(cases)} labelled claims)", "",
             f"Exact match per claim: **{exact}/{len(cases)}** ({result['exact_match_rate']:.1%})", "",
             "| Rule | Support | TP | FP | FN | Precision | Recall | F1 |", "|---|---|---|---|---|---|---|---|"]
    lines += [f"| {r} | {m['support']} | {m['tp']} | {m['fp']} | {m['fn']} | {m['precision']:.2f} | "
              f"{m['recall']:.2f} | {m['f1']:.2f} |" for r, m in per_rule.items()]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    if got != exp:
        print(f"\nMISMATCH: {len(got - exp)} false positives, {len(exp - got)} false negatives (see results.json)")
        sys.exit(1)


if __name__ == "__main__":
    main()
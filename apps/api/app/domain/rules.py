"""Payer rules: pure functions over a ClaimPackage (no I/O).
Severity, confidence, suggested action and parameters live in data/payer-rules/catalogue.json."""
import re
from collections import defaultdict
from typing import Callable, Optional

from pydantic import BaseModel, Field

from app.domain.claim_package import ClaimPackage
from app.domain.finding import Severity

Hit = tuple[str, Optional[int]]  # (evidence, line_no)


class RuleConfig(BaseModel):
    id: str
    name: str
    description: str = ""
    category: str = ""
    severity: Severity
    confidence: float = Field(1.0, ge=0, le=1)
    enabled: bool = True
    suggested_action: str
    params: dict = Field(default_factory=dict)


class BatchContext:
    """Cross-claim facts for duplicate detection. Scope: the claims of the current upload."""

    def __init__(self, claims: list[ClaimPackage]):
        self.by_key: dict[tuple, set[str]] = defaultdict(set)
        for c in claims:
            for l in c.lines:
                if l.service_date:
                    self.by_key[(c.patient.id, l.procedure_code, l.service_date)].add(c.claim_id)


def amt_001(c: ClaimPackage, p: dict, ctx: BatchContext) -> list[Hit]:
    cap, hits = p.get("max_line_amount", 10000), []
    for l in c.lines:
        if l.amount <= 0:
            hits.append((f"lines[line_no={l.line_no}].amount={l.amount} must be greater than 0", l.line_no))
        elif l.amount > cap:
            hits.append((f"lines[line_no={l.line_no}].amount={l.amount} exceeds payer cap {cap}", l.line_no))
    return hits


def qty_001(c, p, ctx) -> list[Hit]:
    mx = p.get("max_quantity", 100)
    return [(f"lines[line_no={l.line_no}].quantity={l.quantity} outside 1..{mx}", l.line_no)
            for l in c.lines if l.quantity <= 0 or l.quantity > mx]


def cov_001(c, p, ctx) -> list[Hit]:
    cov, hits = c.coverage, []
    dates = [("encounter.start", c.encounter.start, None)] + \
            [(f"lines[line_no={l.line_no}].service_date", l.service_date, l.line_no) for l in c.lines]
    for label, d, ln in dates:
        if not d:
            continue
        if cov.start and d < cov.start:
            hits.append((f"{label}={d} is before coverage start {cov.start}", ln))
        elif cov.end and d > cov.end:
            hits.append((f"{label}={d} is after coverage end {cov.end}", ln))
    return hits


def auth_001(c, p, ctx) -> list[Hit]:
    required = {str(x).upper() for x in p.get("procedures_requiring_auth", [])}
    return [(f"lines[line_no={l.line_no}] procedure {l.procedure_code} requires authorization but authorization_id is missing",
             l.line_no) for l in c.lines if l.procedure_code in required and not l.authorization_id]


def dup_001(c, p, ctx) -> list[Hit]:
    seen, hits = {}, []
    for l in c.lines:
        if not l.service_date:
            continue
        key = (l.procedure_code, l.service_date)
        if key in seen:
            hits.append((f"lines[line_no={l.line_no}] repeats procedure {l.procedure_code} on {l.service_date} "
                         f"(first seen on line {seen[key]})", l.line_no))
        else:
            seen[key] = l.line_no
    return hits


def dup_002(c, p, ctx) -> list[Hit]:
    hits = []
    for l in c.lines:
        if not l.service_date:
            continue
        others = ctx.by_key[(c.patient.id, l.procedure_code, l.service_date)] - {c.claim_id}
        if others:
            hits.append((f"lines[line_no={l.line_no}] same patient, procedure {l.procedure_code} and date "
                         f"{l.service_date} as claim(s) {sorted(others)}", l.line_no))
    return hits


def dx_001(c, p, ctx) -> list[Hit]:
    if not c.diagnoses:
        return [("diagnoses is empty: claim has no diagnosis code", None)]
    if not any(d.primary for d in c.diagnoses):
        return [("diagnoses has no primary diagnosis", None)]
    return []


_ICD10 = re.compile(r"^[A-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$")


def dx_002(c, p, ctx) -> list[Hit]:
    return [(f"diagnoses[{i}].code={d.code!r} is not a valid ICD-10 format", None)
            for i, d in enumerate(c.diagnoses) if not _ICD10.match(d.code)]


def prv_001(c, p, ctx) -> list[Hit]:
    npi = c.provider.npi
    if not npi:
        return [("provider.npi is missing", None)]
    if not (npi.isdigit() and len(npi) == 10):
        return [(f"provider.npi={npi!r} must be exactly 10 digits", None)]
    return []


def date_001(c, p, ctx) -> list[Hit]:
    e, hits = c.encounter, []
    if e.start and e.end and e.end < e.start:
        hits.append((f"encounter.end={e.end} is before encounter.start={e.start}", None))
    for l in c.lines:
        d = l.service_date
        if d and ((e.start and d < e.start) or (e.end and d > e.end)):
            hits.append((f"lines[line_no={l.line_no}].service_date={d} is outside the encounter "
                         f"{e.start}..{e.end}", l.line_no))
    return hits


def pat_001(c, p, ctx) -> list[Hit]:
    b = c.patient.birth_date
    if not b:
        return [("patient.birth_date is missing", None)]
    if c.encounter.start and b > c.encounter.start:
        return [(f"patient.birth_date={b} is after encounter.start={c.encounter.start}", None)]
    return []


def cur_001(c, p, ctx) -> list[Hit]:
    hits = [(f"lines[line_no={l.line_no}].currency is missing", l.line_no) for l in c.lines if not l.currency]
    used = sorted({l.currency for l in c.lines if l.currency})
    if len(used) > 1:
        hits.append((f"lines use several currencies: {used}", None))
    return hits


RULES: dict[str, Callable] = {
    "R-AMT-001": amt_001, "R-QTY-001": qty_001, "R-COV-001": cov_001, "R-AUTH-001": auth_001,
    "R-DUP-001": dup_001, "R-DUP-002": dup_002, "R-DX-001": dx_001, "R-DX-002": dx_002,
    "R-PRV-001": prv_001, "R-DATE-001": date_001, "R-PAT-001": pat_001, "R-CUR-001": cur_001,
}
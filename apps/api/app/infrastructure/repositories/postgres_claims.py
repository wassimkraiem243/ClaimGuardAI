"""PostgreSQL adapter for ClaimRepository."""
import json
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.domain.claim_package import ClaimPackage
from app.domain.claim_repository import ClaimConflict
from app.domain.finding import ValidationFinding
from app.infrastructure.audit.postgres_audit import get_engine


def _plain(obj) -> dict:
    return json.loads(json.dumps(obj, default=str))


class PostgresClaimRepository:
    def __init__(self, engine: Optional[Engine] = None):
        self._engine = engine or get_engine()

    def save(self, claim: ClaimPackage, file_sha256: str, received_at: str) -> bool:
        """True if created, False if an identical claim was already stored.
        Raises ClaimConflict if the claim_id exists with different content."""
        package = _plain(claim.model_dump(mode="json"))
        with self._engine.begin() as conn:
            created = conn.execute(
                text("INSERT INTO claims (claim_id, source, patient_id, file_sha256, received_at, package) "
                     "VALUES (:id, :src, :pid, :sha, :at, CAST(:pkg AS jsonb)) "
                     "ON CONFLICT (claim_id) DO NOTHING RETURNING claim_id"),
                {"id": claim.claim_id, "src": claim.source, "pid": claim.patient.id,
                 "sha": file_sha256, "at": received_at, "pkg": json.dumps(package)}).first()
            if created is None:
                stored = conn.execute(text("SELECT package FROM claims WHERE claim_id = :id"),
                                      {"id": claim.claim_id}).scalar_one()
                if _plain(stored) != package:
                    raise ClaimConflict(claim.claim_id)
                return False
            for l in claim.lines:
                conn.execute(
                    text("INSERT INTO claim_lines (claim_id, line_no, procedure_code, service_date) "
                         "VALUES (:id, :n, :proc, :d)"),
                    {"id": claim.claim_id, "n": l.line_no, "proc": l.procedure_code, "d": l.service_date})
            return True

    def save_findings(self, claim_id: str, findings: list[ValidationFinding]) -> None:
        """Replace the stored findings of a claim (re-evaluation overwrites)."""
        with self._engine.begin() as conn:
            conn.execute(text("DELETE FROM findings WHERE claim_id = :id"), {"id": claim_id})
            for f in findings:
                conn.execute(
                    text("INSERT INTO findings (claim_id, rule_id, severity, line_no, data) "
                         "VALUES (:id, :rule, :sev, :ln, CAST(:data AS jsonb))"),
                    {"id": claim_id, "rule": f.rule_id, "sev": f.severity, "ln": f.line_no,
                     "data": json.dumps(_plain(f.model_dump()))})

    def get(self, claim_id: str) -> Optional[dict]:
        with self._engine.connect() as conn:
            return conn.execute(text("SELECT package FROM claims WHERE claim_id = :id"),
                                {"id": claim_id}).scalar()

    def findings_for(self, claim_id: str) -> list[dict]:
        with self._engine.connect() as conn:
            return [r[0] for r in conn.execute(
                text("SELECT data FROM findings WHERE claim_id = :id ORDER BY id"), {"id": claim_id})]

    def prior_services(self, claims: list[ClaimPackage]) -> dict[tuple, set[str]]:
        """Services already stored for the batch's patients, from OTHER claims.
        Key: (patient_id, procedure_code, service_date) -> {claim_id}. Feeds R-DUP-002."""
        pids = sorted({c.patient.id for c in claims})
        own = sorted({c.claim_id for c in claims})
        out: dict[tuple, set[str]] = {}
        if not pids:
            return out
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT c.patient_id, l.procedure_code, l.service_date, c.claim_id "
                     "FROM claim_lines l JOIN claims c USING (claim_id) "
                     "WHERE c.patient_id = ANY(:pids) AND c.claim_id <> ALL(:own) "
                     "AND l.service_date IS NOT NULL"),
                {"pids": pids, "own": own})
            for pid, proc, d, cid in rows:
                out.setdefault((pid, proc, d), set()).add(cid)
        return out
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.domain.claim_package import ClaimPackage, IngestionRejected
from app.domain.finding import ValidationFinding
from app.domain.audit import AuditLog
from app.infrastructure.audit.factory import get_audit_log
from app.infrastructure.parsers.csv_parser import CsvClaimParser
from app.infrastructure.parsers.fhir_parser import FhirClaimParser
from app.infrastructure.parsers.preflight import InputRejected, check_fhir, prepare_csv, reject_duplicate_ids
from app.infrastructure.rules.catalogue import load_catalogue
from app.services.evaluate_claims import EvaluateClaims
from app.services.ingest_claim import IngestClaim

MAX_BYTES = 5 * 1024 * 1024  # minimization / DoS guard
SCHEMA_VERSION = "1.0"


class PrettyJSONResponse(JSONResponse):
    """Indented UTF-8 JSON so responses are readable in a terminal and in the demo."""

    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False, indent=2).encode("utf-8")


router = APIRouter(prefix="/claims", tags=["claims"], default_response_class=PrettyJSONResponse)


class InputMeta(BaseModel):
    filename: str
    format: str          # CSV | FHIR
    bytes: int
    sha256: str
    received_at: str


class EvaluationResult(BaseModel):
    schema_version: str = SCHEMA_VERSION
    meta: InputMeta
    summary: dict
    claims: list[ClaimPackage]
    findings: list[ValidationFinding]


def _select_parser(filename: str | None):
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return "CSV", CsvClaimParser()
    if name.endswith(".json"):
        return "FHIR", FhirClaimParser()
    raise HTTPException(415, "Unsupported file type: upload a .csv or a .json (FHIR Bundle)")


async def _ingest(file: UploadFile, audit: AuditLog) -> tuple[list[ClaimPackage], InputMeta]:
    fmt, parser = _select_parser(file.filename)
    raw = await file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "File too large")
    meta = InputMeta(filename=file.filename or "", format=fmt, bytes=len(raw),
                     sha256=hashlib.sha256(raw).hexdigest(),
                     received_at=datetime.now(timezone.utc).isoformat())
    try:
        clean = prepare_csv(raw) if fmt == "CSV" else check_fhir(raw)
        claims = IngestClaim(parser).execute(clean)
        reject_duplicate_ids(claims)
    except (IngestionRejected, InputRejected) as e:
        audit.append("INGESTION_REJECTED", getattr(e, "claim_id", None),
                     {**e.to_dict(), "file": file.filename, "sha256": meta.sha256})
        raise HTTPException(400, detail=e.to_dict())
    for c in claims:
        audit.append("CLAIM_INGESTED", c.claim_id, {"source": c.source, "file": file.filename, "sha256": meta.sha256,
                                                    "lines": len(c.lines), "warnings": c.ingestion_warnings})
    return claims, meta


@router.post("/ingest", response_model=list[ClaimPackage])
async def ingest(file: UploadFile = File(...)):
    claims, _ = await _ingest(file, get_audit_log())
    return claims


@router.post("/ingest-and-evaluate", response_model=EvaluationResult)
async def ingest_and_evaluate(file: UploadFile = File(...)):
    audit = get_audit_log()
    claims, meta = await _ingest(file, audit)
    findings = EvaluateClaims(load_catalogue()).execute(claims)
    for f in findings:
        audit.append("FINDING_RAISED", f.claim_id, f.model_dump())
    flagged = {f.claim_id for f in findings}
    for c in claims:
        own = [f for f in findings if f.claim_id == c.claim_id]
        audit.append("CLAIM_EVALUATED", c.claim_id, {"findings": len(own), "rule_ids": sorted({f.rule_id for f in own})})
    summary = {
        "claims": len(claims),
        "claims_with_findings": len(flagged),
        "claims_clean": len(claims) - len(flagged),
        "findings": len(findings),
        "by_severity": dict(Counter(f.severity for f in findings)),
        "by_category": dict(Counter(f.category for f in findings)),
        "by_rule": dict(Counter(f.rule_id for f in findings)),
    }
    return EvaluationResult(meta=meta, summary=summary, claims=claims, findings=findings)


@router.get("/audit")
def read_audit(claim_id: Optional[str] = None):
    return get_audit_log().read(claim_id)


@router.get("/audit/verify")
def verify_audit():
    audit = get_audit_log()
    ok, bad = audit.verify()
    return {"valid": ok, "first_invalid_seq": bad, "events": len(audit.read())}
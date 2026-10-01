from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.deps import require_api_key
from app.domain.claim_package import IngestionRejected
from app.domain.normalized_claim import NormalizedClaim
from app.services.ingest_claim import ingest_upload

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


@router.post("/ingest", response_model=list[NormalizedClaim])
async def ingest(file: UploadFile = File(...)):
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "File too large")
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



@router.get("/audit/verify")
def verify_audit():
    audit = get_audit_log()
    ok, bad = audit.verify()
    return {"valid": ok, "first_invalid_seq": bad, "events": len(audit.read())}
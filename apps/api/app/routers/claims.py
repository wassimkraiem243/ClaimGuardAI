from fastapi import APIRouter, File, HTTPException, UploadFile

from app.domain.claim_package import ClaimPackage, IngestionRejected
from app.infrastructure.parsers.csv_parser import CsvClaimParser
from app.services.ingest_claim import IngestClaim

router = APIRouter(prefix="/claims", tags=["claims"])
MAX_BYTES = 5 * 1024 * 1024  # minimization / DoS guard


@router.post("/ingest", response_model=list[ClaimPackage])
async def ingest(file: UploadFile = File(...)):
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "File too large")
    use_case = IngestClaim(CsvClaimParser())  # TODO: pick parser by content-type / extension (FHIR)
    try:
        return use_case.execute(raw)
    except IngestionRejected as e:
        # TODO(audit teammate): write e.to_dict() as an AuditEvent here
        raise HTTPException(400, detail=e.to_dict())
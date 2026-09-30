from fastapi import APIRouter, File, HTTPException, UploadFile

from app.domain.claim_package import ClaimPackage, IngestionRejected
from app.infrastructure.parsers.csv_parser import CsvClaimParser
from app.infrastructure.parsers.fhir_parser import FhirClaimParser
from app.services.ingest_claim import IngestClaim

router = APIRouter(prefix="/claims", tags=["claims"])
MAX_BYTES = 5 * 1024 * 1024  # minimization / DoS guard


def _select_parser(filename: str | None):
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return CsvClaimParser()
    if name.endswith(".json"):
        return FhirClaimParser()
    raise HTTPException(415, "Unsupported file type: upload a .csv or a .json (FHIR Bundle)")


@router.post("/ingest", response_model=list[ClaimPackage])
async def ingest(file: UploadFile = File(...)):
    parser = _select_parser(file.filename)
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "File too large")
    try:
        return IngestClaim(parser).execute(raw)
    except IngestionRejected as e:
        # TODO(audit teammate): write e.to_dict() as an AuditEvent here
        raise HTTPException(400, detail=e.to_dict())
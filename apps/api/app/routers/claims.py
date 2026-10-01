from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.deps import require_api_key
from app.domain.claim_package import ClaimPackage, IngestionRejected
from app.services.ingest_claim import ingest_upload

router = APIRouter(
    prefix="/claims",
    tags=["claims"],
    dependencies=[Depends(require_api_key)],
)
MAX_BYTES = 5 * 1024 * 1024  # minimization / DoS guard


@router.post("/ingest", response_model=list[ClaimPackage])
async def ingest(file: UploadFile = File(...)):
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "File too large")
    try:
        return ingest_upload(file.filename, raw)
    except ValueError as e:
        raise HTTPException(415, str(e)) from e
    except IngestionRejected as e:
        # TODO(audit): persist e.to_dict() as INGESTION_REJECTED before returning 400
        raise HTTPException(400, detail=e.to_dict()) from e
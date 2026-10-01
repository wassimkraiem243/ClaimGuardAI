from fastapi import APIRouter, Depends, HTTPException

from app.deps import require_api_key
from app.infrastructure.rule_engine.audit_hook import AuditError
from app.infrastructure.rule_engine.core.engine import IngestionError
from app.infrastructure.rule_engine.schemas import BatchRequest, BatchResponse, ValidateRequest
from app.services import rule_validation

router = APIRouter(
    prefix="/v1",
    tags=["validation"],
    dependencies=[Depends(require_api_key)],
)


def _audit_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"error": "audit_unavailable", "message": str(exc)},
    )


@router.post("/validate")
def validate(req: ValidateRequest):
    prev = (
        (req.previous_run.run_id, req.previous_run.input_hash)
        if req.previous_run
        else None
    )
    try:
        return rule_validation.validate_envelope(
            req.claim, req.policy_override, previous_run=prev
        )
    except IngestionError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "ingestion_error", "message": str(e), "details": e.details},
        ) from e
    except (AuditError, OSError) as e:
        raise _audit_unavailable(e) from e


@router.post("/validate/batch", response_model=BatchResponse)
def validate_batch(req: BatchRequest):
    try:
        return rule_validation.validate_batch(req.claims, req.policy_override)
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    except (AuditError, OSError) as e:
        raise _audit_unavailable(e) from e

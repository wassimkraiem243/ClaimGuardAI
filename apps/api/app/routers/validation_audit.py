import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.deps import require_api_key
from app.infrastructure import audit_log as audit
from app.infrastructure.audit_log import AuditError

router = APIRouter(
    prefix="/v1/audit",
    tags=["audit"],
    dependencies=[Depends(require_api_key)],
)


def _log_path() -> str:
    return str(settings.resolved_audit_log())


@router.get("/verify")
def verify_chain():
    try:
        head, count = audit.verify(_log_path())
    except AuditError as e:
        raise HTTPException(503, detail=str(e)) from e
    return {"valid": True, "events": count, "head_hash": head}


@router.get("/summary")
def audit_summary():
    try:
        audit.verify(_log_path())
        return audit.summary(_log_path())
    except AuditError as e:
        raise HTTPException(503, detail=str(e)) from e


@router.get("/trace")
def audit_trace(
    claim_id: str = Query(..., min_length=1),
    fast: bool = Query(False, description="Skip full-chain verify before read"),
):
    try:
        rows = audit.trace(_log_path(), claim_id, verify_chain=not fast)
    except AuditError as e:
        raise HTTPException(503, detail=str(e)) from e
    return {"claim_id": claim_id, "events": rows}


@router.get("/feedback")
def human_feedback(limit: int = Query(50, ge=1, le=500)):
    """Active-learning export: recent human review decisions from the hash-chained audit log."""
    path = _log_path()
    if not path or not __import__("pathlib").Path(path).exists():
        return {"decisions": []}
    decisions: list[dict] = []
    try:
        with open(path, "rb") as f:
            for raw in f:
                if not raw.strip():
                    continue
                row = json.loads(raw)
                event = row.get("event") or {}
                if "action" not in event:
                    continue
                decisions.append(
                    {
                        "sequence": row.get("sequence"),
                        "recorded_at": row.get("recorded_at"),
                        "actor": event.get("actor"),
                        "action": event.get("action"),
                        "claim_id": event.get("claim_id"),
                        "rule_id": event.get("rule_id"),
                        "reason": event.get("reason"),
                        "original_status": event.get("original_status"),
                    }
                )
    except (OSError, json.JSONDecodeError) as e:
        raise HTTPException(503, detail=str(e)) from e
    return {"decisions": decisions[-limit:]}

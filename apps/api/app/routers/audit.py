from typing import Optional

from fastapi import APIRouter

from app.infrastructure.audit.factory import get_audit_log
from app.routers.claims import PrettyJSONResponse

router = APIRouter(prefix="/claims", tags=["audit"], default_response_class=PrettyJSONResponse)


@router.get("/audit")
def read_audit(claim_id: Optional[str] = None):
    return get_audit_log().read(claim_id)


@router.get("/audit/verify")
def verify_audit():
    audit = get_audit_log()
    ok, bad = audit.verify()
    return {"valid": ok, "first_invalid_seq": bad, "events": len(audit.read())}
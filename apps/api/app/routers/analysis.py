from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_role
from app.services import analysis as analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get(
    "/findings/{finding_id}",
    dependencies=[Depends(require_role("analyst", "auditor"))],
)
def get_finding_analysis(finding_id: str, db: Session = Depends(get_db)):
    return analysis_service.get_finding_analysis(db, finding_id)


@router.post("/findings/{finding_id}")
async def trigger_finding_analysis(
    finding_id: str,
    force: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("analyst")),
):
    if force == "true" and user["role"] != "admin":
        raise HTTPException(403, "force requires admin")
    return await analysis_service.analyze_finding(
        db, finding_id, force=force == "true"
    )
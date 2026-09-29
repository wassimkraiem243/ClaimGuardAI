from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_api_key
from app.repositories.store import FindingRepository

router = APIRouter(prefix="/metrics", tags=["metrics"], dependencies=[Depends(require_api_key)])


@router.get("")
def metrics(
    project_id: str | None = None,
    pipeline_run_id: str | None = None,
    db: Session = Depends(get_db),
):
    repo = FindingRepository(db)
    filters = {}
    if project_id:
        filters["projectId"] = project_id
    if pipeline_run_id:
        filters["pipelineRunId"] = pipeline_run_id
    by_severity = repo.count_by_severity(filters)
    total = sum(by_severity.values())
    return {"totalFindings": total, "bySeverity": by_severity}

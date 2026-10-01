from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.mappers.findings import finding_context_from_row, to_unified_finding
from app.repositories.store import FindingRepository

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("")
def list_findings(
    project_id: str | None = None,
    pipeline_run_id: str | None = None,
    scan_execution_id: str | None = None,
    tool: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    repo = FindingRepository(db)
    filters = {
        "projectId": project_id,
        "pipelineRunId": pipeline_run_id,
        "scanExecutionId": scan_execution_id,
        "tool": tool,
        "severity": severity,
        "category": category,
        "limit": limit or 500,
        "offset": offset or 0,
    }
    rows = repo.find_with_context(filters)
    return [
        to_unified_finding(finding_context_from_row(finding, scan))
        for finding, scan in rows
    ]
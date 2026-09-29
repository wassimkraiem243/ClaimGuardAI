from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_api_key
from app.services.dashboard import get_dashboard_overview, list_pipeline_runs

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_api_key)])


@router.get("/overview")
def overview(
    project_slug: str = "claimguard-demo",
    pipeline_run_id: str | None = None,
    db: Session = Depends(get_db),
):
    return get_dashboard_overview(db, project_slug, pipeline_run_id)


@router.get("/pipeline-runs")
def pipeline_runs(project_slug: str = "claimguard-demo", db: Session = Depends(get_db)):
    return list_pipeline_runs(db, project_slug)

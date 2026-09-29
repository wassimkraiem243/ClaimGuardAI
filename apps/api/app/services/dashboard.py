from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.store import (
    FindingRepository,
    PipelineRunRepository,
    ProjectRepository,
)


def get_dashboard_overview(
    db: Session,
    project_slug: str,
    pipeline_run_id: str | None,
) -> dict:
    projects = ProjectRepository(db)
    runs = PipelineRunRepository(db)
    findings = FindingRepository(db)

    project = projects.find_by_slug(project_slug)
    if not project:
        raise HTTPException(
            status_code=400,
            detail=f'Project "{project_slug}" not found. Run scripts/seed.py to create it.',
        )

    latest = runs.find_latest_by_project_id(project.id)
    selected = _resolve_run(db, project.id, pipeline_run_id, latest)

    filters: dict = {"projectId": project.id}
    if selected:
        filters["pipelineRunId"] = selected.id

    by_severity = findings.count_by_severity(filters)
    by_category = findings.count_by_category(filters)
    scans = runs.find_scan_summaries(selected.id) if selected else []
    total = sum(by_severity.values())

    last_received = None
    if selected:
        last_received = selected.finishedAt or selected.updatedAt

    return {
        "project": {
            "id": project.id,
            "slug": project.slug,
            "name": project.name,
        },
        "hasData": total > 0 or len(scans) > 0,
        "lastReceivedAt": last_received.isoformat() if last_received else None,
        "latestPipelineRun": (
            {
                "id": selected.id,
                "externalId": selected.externalId,
                "status": selected.status,
                "branch": selected.branch,
                "commitSha": selected.commitSha,
                "finishedAt": selected.finishedAt.isoformat()
                if selected.finishedAt
                else None,
            }
            if selected
            else None
        ),
        "metrics": {
            "totalFindings": total,
            "bySeverity": by_severity,
            "byCategory": by_category,
        },
        "scans": scans,
    }


def list_pipeline_runs(db: Session, project_slug: str) -> list[dict]:
    projects = ProjectRepository(db)
    runs = PipelineRunRepository(db)

    project = projects.find_by_slug(project_slug)
    if not project:
        raise HTTPException(
            status_code=400,
            detail=f'Project "{project_slug}" not found. Run scripts/seed.py to create it.',
        )

    items = runs.find_by_project_id(project.id)
    return [
        {
            "id": run.id,
            "projectId": run.projectId,
            "externalId": run.externalId,
            "branch": run.branch,
            "commitSha": run.commitSha,
            "status": run.status,
            "startedAt": run.startedAt.isoformat() if run.startedAt else None,
            "finishedAt": run.finishedAt.isoformat() if run.finishedAt else None,
            "createdAt": run.createdAt.isoformat(),
            "updatedAt": run.updatedAt.isoformat(),
        }
        for run in items
    ]


def _resolve_run(
    db: Session,
    project_id: str,
    pipeline_run_id: str | None,
    latest,
):
    runs = PipelineRunRepository(db)
    if not pipeline_run_id:
        return latest
    run = runs.find_by_id(pipeline_run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f'Pipeline run "{pipeline_run_id}" not found.')
    if run.projectId != project_id:
        raise HTTPException(
            status_code=400,
            detail=f'Pipeline run "{pipeline_run_id}" does not belong to this project.',
        )
    return run

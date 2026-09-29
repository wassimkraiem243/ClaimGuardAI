from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Finding, PipelineRun, Project, ScanExecution


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_slug(self, slug: str) -> Project | None:
        return self._db.scalar(select(Project).where(Project.slug == slug))


class PipelineRunRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, run_id: str) -> PipelineRun | None:
        return self._db.get(PipelineRun, run_id)

    def find_latest_by_project_id(self, project_id: str) -> PipelineRun | None:
        stmt = (
            select(PipelineRun)
            .where(PipelineRun.projectId == project_id)
            .order_by(PipelineRun.createdAt.desc())
            .limit(1)
        )
        return self._db.scalar(stmt)

    def find_by_project_id(self, project_id: str, limit: int = 50) -> list[PipelineRun]:
        stmt = (
            select(PipelineRun)
            .where(PipelineRun.projectId == project_id)
            .order_by(PipelineRun.createdAt.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def find_scan_summaries(self, pipeline_run_id: str) -> list[dict]:
        stmt = (
            select(
                ScanExecution.tool,
                ScanExecution.scanLabel,
                ScanExecution.status,
                ScanExecution.finishedAt,
                func.count(Finding.id).label("findingsCount"),
            )
            .outerjoin(Finding, Finding.scanExecutionId == ScanExecution.id)
            .where(ScanExecution.pipelineRunId == pipeline_run_id)
            .group_by(
                ScanExecution.id,
                ScanExecution.tool,
                ScanExecution.scanLabel,
                ScanExecution.status,
                ScanExecution.finishedAt,
                ScanExecution.createdAt,
            )
            .order_by(ScanExecution.createdAt.asc())
        )
        rows = self._db.execute(stmt).all()
        return [
            {
                "tool": row.tool,
                "scanLabel": row.scanLabel,
                "status": row.status,
                "findingsCount": row.findingsCount,
                "finishedAt": row.finishedAt.isoformat() if row.finishedAt else None,
            }
            for row in rows
        ]


class FindingRepository:
    SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN")
    CATEGORIES = ("SECRET", "SAST", "SCA", "CONTAINER", "DAST")

    def __init__(self, db: Session) -> None:
        self._db = db

    def _base_stmt(self, filters: dict):
        stmt = select(Finding).join(ScanExecution).join(PipelineRun).join(Project)
        if filters.get("projectId"):
            stmt = stmt.where(PipelineRun.projectId == filters["projectId"])
        if filters.get("pipelineRunId"):
            stmt = stmt.where(PipelineRun.id == filters["pipelineRunId"])
        if filters.get("scanExecutionId"):
            stmt = stmt.where(Finding.scanExecutionId == filters["scanExecutionId"])
        if filters.get("tool"):
            stmt = stmt.where(ScanExecution.tool == filters["tool"])
        if filters.get("severity"):
            stmt = stmt.where(Finding.severity == filters["severity"])
        if filters.get("category"):
            stmt = stmt.where(Finding.category == filters["category"])
        return stmt

    def find_with_context(self, filters: dict) -> list[tuple[Finding, ScanExecution]]:
        stmt = (
            self._base_stmt(filters)
            .options(
                joinedload(Finding.scanExecution).joinedload(ScanExecution.pipelineRun)
            )
            .order_by(Finding.severity.asc(), Finding.createdAt.desc())
            .limit(filters.get("limit", 500))
            .offset(filters.get("offset", 0))
        )
        findings = list(self._db.scalars(stmt).unique())
        return [(f, f.scanExecution) for f in findings]

    def find_by_id_with_context(
        self, finding_id: str
    ) -> tuple[Finding, ScanExecution] | None:
        stmt = (
            select(Finding)
            .where(Finding.id == finding_id)
            .options(
                joinedload(Finding.scanExecution).joinedload(ScanExecution.pipelineRun)
            )
        )
        finding = self._db.scalar(stmt)
        if not finding:
            return None
        return finding, finding.scanExecution

    def count_by_severity(self, filters: dict) -> dict[str, int]:
        counts = {s: 0 for s in self.SEVERITIES}
        stmt = (
            select(Finding.severity, func.count())
            .select_from(Finding)
            .join(ScanExecution)
            .join(PipelineRun)
        )
        if filters.get("projectId"):
            stmt = stmt.where(PipelineRun.projectId == filters["projectId"])
        if filters.get("pipelineRunId"):
            stmt = stmt.where(PipelineRun.id == filters["pipelineRunId"])
        stmt = stmt.group_by(Finding.severity)
        for severity, count in self._db.execute(stmt):
            counts[severity] = count
        return counts

    def count_by_category(self, filters: dict) -> dict[str, int]:
        counts = {c: 0 for c in self.CATEGORIES}
        stmt = (
            select(Finding.category, func.count())
            .select_from(Finding)
            .join(ScanExecution)
            .join(PipelineRun)
        )
        if filters.get("projectId"):
            stmt = stmt.where(PipelineRun.projectId == filters["projectId"])
        if filters.get("pipelineRunId"):
            stmt = stmt.where(PipelineRun.id == filters["pipelineRunId"])
        stmt = stmt.group_by(Finding.category)
        for category, count in self._db.execute(stmt):
            if category:
                counts[category] = count
        return counts

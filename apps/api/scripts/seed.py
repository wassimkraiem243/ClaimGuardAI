"""Seed demo project, sample dashboard findings, and dev JWT user."""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from sqlalchemy import select

load_dotenv()

from app import security  # noqa: E402
from app.config import settings  # noqa: E402
from app.db.models import Finding, PipelineRun, Project, ScanExecution  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.infrastructure.repositories.postgres_users import PostgresUserRepository  # noqa: E402

DEMO_USER = "demo"
DEMO_PASSWORD = "claimguard-demo!"  # dev only — 16 chars, meets create_user policy
DEMO_FINDINGS = [
    {
        "id": "finding-r007-demo",
        "fingerprint": "fp-r007-line-arithmetic",
        "title": "Line amount differs from quantity × unit price (R007)",
        "description": "Claim line L2 net amount does not match arithmetic on the envelope.",
        "severity": "HIGH",
        "category": "SAST",
        "ruleId": "R007",
        "recommendation": "Reconcile quantity, unit price, and line net amount before resubmission.",
    },
    {
        "id": "finding-r012-demo",
        "fingerprint": "fp-r012-total",
        "title": "Claim total mismatch (R012)",
        "description": "Sum of line amounts differs from declared total_amount on the claim.",
        "severity": "HIGH",
        "category": "SAST",
        "ruleId": "R012",
        "recommendation": "Update total_amount or line amounts so they match exactly.",
    },
    {
        "id": "finding-r003-demo",
        "fingerprint": "fp-r003-coverage",
        "title": "Coverage not active on service date (R003)",
        "description": "Member coverage window does not include the encounter service date.",
        "severity": "MEDIUM",
        "category": "SAST",
        "ruleId": "R003",
        "recommendation": "Verify coverage effective/end dates against encounter.service_date.",
    },
]


def _upsert_demo_user() -> None:
    repo = PostgresUserRepository()
    existing = repo.get(DEMO_USER)
    hashed = security.hash_password(DEMO_PASSWORD)
    if existing:
        return
    repo.create(DEMO_USER, hashed, "analyst")
    print(f"Seeded user: {DEMO_USER} / {DEMO_PASSWORD} (analyst)")


def main() -> None:
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        project = db.scalar(select(Project).where(Project.slug == "claimguard-demo"))
        if not project:
            project = Project(
                id=str(uuid.uuid4()),
                name="ClaimGuard Demo",
                slug="claimguard-demo",
                repository="https://gitlab.com/example/claimguard-demo",
                createdAt=now,
                updatedAt=now,
            )
            db.add(project)
            db.flush()
        else:
            project.name = "ClaimGuard Demo"
            project.updatedAt = now

        run = db.scalar(
            select(PipelineRun).where(
                PipelineRun.projectId == project.id,
                PipelineRun.externalId == "demo-validation-batch",
            )
        )
        if not run:
            run = PipelineRun(
                id=str(uuid.uuid4()),
                projectId=project.id,
                externalId="demo-validation-batch",
                branch="main",
                commitSha="demo",
                status="SUCCESS",
                startedAt=now,
                finishedAt=now,
                createdAt=now,
                updatedAt=now,
            )
            db.add(run)
            db.flush()

        scan = db.scalar(
            select(ScanExecution).where(
                ScanExecution.pipelineRunId == run.id,
                ScanExecution.tool == "SEMGREP",
                ScanExecution.scanLabel == "claimguard-rules",
            )
        )
        if not scan:
            scan = ScanExecution(
                id=str(uuid.uuid4()),
                pipelineRunId=run.id,
                tool="SEMGREP",
                scanLabel="claimguard-rules",
                status="SUCCESS",
                startedAt=now,
                finishedAt=now,
                createdAt=now,
                updatedAt=now,
            )
            db.add(scan)
            db.flush()

        for spec in DEMO_FINDINGS:
            row = db.get(Finding, spec["id"])
            if row:
                continue
            db.add(
                Finding(
                    id=spec["id"],
                    scanExecutionId=scan.id,
                    fingerprint=spec["fingerprint"],
                    title=spec["title"],
                    description=spec["description"],
                    severity=spec["severity"],
                    category=spec["category"],
                    ruleId=spec["ruleId"],
                    recommendation=spec["recommendation"],
                    createdAt=now,
                    updatedAt=now,
                )
            )

        db.commit()
        print("Seeded project: claimguard-demo (with demo rule findings for AI dashboard)")
    finally:
        db.close()

    try:
        _upsert_demo_user()
    except Exception as e:
        print(f"Note: demo user not created ({e}). Set CLAIMGUARD_JWT_SECRET and run migrations.")


if __name__ == "__main__":
    main()

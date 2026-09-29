"""Seed demo project for local development."""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from sqlalchemy import select

load_dotenv()

from app.config import settings  # noqa: E402
from app.db.models import Project  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def main() -> None:
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        existing = db.scalar(select(Project).where(Project.slug == "claimguard-demo"))
        if existing:
            existing.name = "ClaimGuard Demo"
            existing.repository = "https://gitlab.com/example/claimguard-demo"
            existing.updatedAt = now
        else:
            db.add(
                Project(
                    id=str(uuid.uuid4()),
                    name="ClaimGuard Demo",
                    slug="claimguard-demo",
                    repository="https://gitlab.com/example/claimguard-demo",
                    createdAt=now,
                    updatedAt=now,
                )
            )
        db.commit()
        print("Seeded project: claimguard-demo")
    finally:
        db.close()


if __name__ == "__main__":
    main()

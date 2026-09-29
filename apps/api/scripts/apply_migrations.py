"""Apply SQL migrations under db/migrations in chronological order."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

from app.config import settings  # noqa: E402


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "db" / "migrations"
    folders = sorted(p for p in root.iterdir() if p.is_dir())
    engine = create_engine(settings.database_url)

    with engine.begin() as conn:
        for folder in folders:
            sql_file = folder / "migration.sql"
            if not sql_file.exists():
                continue
            print(f"Applying {folder.name}...")
            conn.execute(text(sql_file.read_text(encoding="utf-8")))

    print("Migrations applied.")


if __name__ == "__main__":
    main()

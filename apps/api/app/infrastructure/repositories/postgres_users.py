"""User storage (PostgreSQL). Passwords arrive already hashed."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.infrastructure.audit.postgres_audit import get_engine


class PostgresUserRepository:
    def __init__(self, engine: Optional[Engine] = None):
        self._engine = engine or get_engine()

    def get(self, username: str) -> Optional[dict]:
        with self._engine.connect() as conn:
            row = conn.execute(text("SELECT username, password_hash, role, disabled FROM users "
                                    "WHERE username = :u"), {"u": username}).first()
        return dict(row._mapping) if row else None

    def create(self, username: str, password_hash: str, role: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("INSERT INTO users (username, password_hash, role, created_at) "
                              "VALUES (:u, :h, :r, :t)"),
                         {"u": username, "h": password_hash, "r": role,
                          "t": datetime.now(timezone.utc).isoformat()})
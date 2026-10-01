"""Hash-chained audit log in PostgreSQL. Same contract as JsonlAuditLog.
append() runs in ONE transaction: take an advisory lock, read the tail, insert seq+1.
Concurrent appenders queue on the lock, so the chain cannot fork (even on an empty table)."""
import json
import os
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.domain.audit import AuditEvent
from app.infrastructure.audit.jsonl_audit import GENESIS, _digest

DEFAULT_URL = "postgresql+psycopg://claimguard:claimguard_dev@localhost:55432/claimguard"
_LOCK_KEY = 727_001  # arbitrary app-wide constant for the audit chain
_engines: dict[str, Engine] = {}


def get_engine(url: Optional[str] = None) -> Engine:
    url = url or os.environ.get("CLAIMGUARD_DATABASE_URL") or DEFAULT_URL
    if url not in _engines:
        _engines[url] = create_engine(url, pool_size=10, pool_pre_ping=True)
    return _engines[url]


class PostgresAuditLog:
    def __init__(self, engine: Optional[Engine] = None, table: str = "audit_events"):
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", table):
            raise ValueError(f"invalid table name: {table!r}")
        self._engine, self._t = engine or get_engine(), table

    def append(self, type: str, claim_id: Optional[str], details: dict) -> AuditEvent:
        with self._engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _LOCK_KEY})
            last = conn.execute(text(f"SELECT seq, hash FROM {self._t} ORDER BY seq DESC LIMIT 1")).first()
            seq, prev = (last[0], last[1]) if last else (0, GENESIS)
            payload = {"seq": seq + 1, "ts": datetime.now(timezone.utc).isoformat(),
                       "type": type, "claim_id": claim_id,
                       "details": json.loads(json.dumps(details, default=str))}
            row = {**payload, "prev_hash": prev, "hash": _digest(prev, payload)}
            conn.execute(
                text(f"INSERT INTO {self._t} (seq, ts, type, claim_id, details, prev_hash, hash) "
                     "VALUES (:seq, :ts, :type, :claim_id, CAST(:details AS jsonb), :prev_hash, :hash)"),
                {**row, "details": json.dumps(row["details"])})
            return AuditEvent(**row)

    def _rows(self, claim_id: Optional[str] = None) -> list[dict]:
        q = f"SELECT seq, ts, type, claim_id, details, prev_hash, hash FROM {self._t}"
        params: dict = {}
        if claim_id is not None:
            q += " WHERE claim_id = :c"
            params["c"] = claim_id
        with self._engine.connect() as conn:
            return [dict(r._mapping) for r in conn.execute(text(q + " ORDER BY seq"), params)]

    def read(self, claim_id: Optional[str] = None) -> list[AuditEvent]:
        return [AuditEvent(**r) for r in self._rows(claim_id)]

    def verify(self) -> tuple[bool, Optional[int]]:
        prev = GENESIS
        for i, r in enumerate(self._rows(), start=1):
            payload = {k: r[k] for k in ("seq", "ts", "type", "claim_id", "details")}
            if r["seq"] != i or r["prev_hash"] != prev or r["hash"] != _digest(prev, payload):
                return False, i
            prev = r["hash"]
        return True, None
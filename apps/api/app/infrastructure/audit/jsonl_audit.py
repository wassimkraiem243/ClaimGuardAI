"""Append-only, hash-chained audit log stored as JSON lines.
Each event's hash covers its content plus the previous hash, so editing or deleting any past
event breaks the chain and verify() reports the first broken sequence number."""
import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.domain.audit import AuditEvent

GENESIS = "0" * 64
_LOCK = threading.Lock()  # shared: the router builds one JsonlAuditLog per request
# .../apps/api/app/infrastructure/audit/jsonl_audit.py -> repo root is parents[5]
DEFAULT_PATH = Path(__file__).resolve().parents[5] / "data" / "audit" / "audit.jsonl"


def _digest(prev: str, payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256((prev + body).encode("utf-8")).hexdigest()


class JsonlAuditLog:
    def __init__(self, path: str | os.PathLike | None = None):
        self._path = Path(path or os.environ.get("CLAIMGUARD_AUDIT_PATH") or DEFAULT_PATH)
        self._lock = _LOCK

    def _rows(self) -> list[dict]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def append(self, type: str, claim_id: Optional[str], details: dict) -> AuditEvent:
        with self._lock:
            rows = self._rows()
            prev = rows[-1]["hash"] if rows else GENESIS
            payload = {"seq": len(rows) + 1, "ts": datetime.now(timezone.utc).isoformat(),
                       "type": type, "claim_id": claim_id, "details": json.loads(json.dumps(details, default=str))}
            row = {**payload, "prev_hash": prev, "hash": _digest(prev, payload)}
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, sort_keys=True) + "\n")
            return AuditEvent(**row)

    def read(self, claim_id: Optional[str] = None) -> list[AuditEvent]:
        return [AuditEvent(**r) for r in self._rows() if claim_id is None or r["claim_id"] == claim_id]

    def verify(self) -> tuple[bool, Optional[int]]:
        prev = GENESIS
        for i, r in enumerate(self._rows(), start=1):
            payload = {k: r[k] for k in ("seq", "ts", "type", "claim_id", "details")}
            if r["seq"] != i or r["prev_hash"] != prev or r["hash"] != _digest(prev, payload):
                return False, i
            prev = r["hash"]
        return True, None
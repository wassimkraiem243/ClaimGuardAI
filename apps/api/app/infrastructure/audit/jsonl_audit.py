"""Append-only, hash-chained audit log stored as JSON lines.
Each event's hash covers its content plus the previous hash, so editing or deleting a past
event breaks the chain and verify() reports the first broken sequence number.

Performance: opening a just-written file is slow on some Windows setups (~20 ms), so each
process keeps ONE append handle per log file plus the last (seq, hash). The cache is checked
against the file size on every call; any outside change (another process, tampering)
triggers a re-read of the tail. Safe across threads (lock) and processes (file lock)."""
import atexit
import hashlib
import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Iterator, Optional

from app.domain.audit import AuditEvent

GENESIS = "0" * 64
# .../apps/api/app/infrastructure/audit/jsonl_audit.py -> repo root is parents[5]
DEFAULT_PATH = Path(__file__).resolve().parents[5] / "data" / "audit" / "audit.jsonl"
_THREAD_LOCK = threading.Lock()
_BLOCK = 4096


def _digest(prev: str, payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256((prev + body).encode("utf-8")).hexdigest()


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    """Cross-process lock on a sidecar .lock file (msvcrt on Windows, flock elsewhere)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + ".lock", "a+b") as lf:
        if os.name == "nt":
            import msvcrt
            while True:
                try:
                    lf.seek(0)
                    msvcrt.locking(lf.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    continue
            try:
                yield
            finally:
                lf.seek(0)
                msvcrt.locking(lf.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)


def _tail(f: BinaryIO) -> tuple[int, str]:
    """(seq, hash) of the last event in an open binary file, read from the end.
    Returns (0, GENESIS) for an empty file."""
    f.seek(0, os.SEEK_END)
    pos, data = f.tell(), b""
    while pos > 0:
        step = min(_BLOCK, pos)
        pos -= step
        f.seek(pos)
        data = f.read(step) + data
        if len(data.rstrip(b"\r\n").split(b"\n")) > 1:  # a newline precedes the last line
            break
    last = data.rstrip(b"\r\n").split(b"\n")[-1].strip()
    if not last:
        return 0, GENESIS
    row = json.loads(last)
    return row["seq"], row["hash"]


class _Open:
    """One cached append handle plus the tail state it had when we last looked."""
    __slots__ = ("f", "size", "seq", "hash")

    def __init__(self, f: BinaryIO):
        self.f, self.size, self.seq, self.hash = f, -1, 0, GENESIS


_OPEN: dict[str, _Open] = {}


def _get_open(path: Path) -> _Open:
    key = str(path)
    o = _OPEN.get(key)
    if o is not None and not path.exists():  # file removed under us: drop the stale handle
        o.f.close()
        del _OPEN[key]
        o = None
    if o is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        o = _Open(open(path, "a+b"))
        _OPEN[key] = o
    return o


def close_all() -> None:
    """Close every cached handle (called at exit; handy in tests on Windows)."""
    with _THREAD_LOCK:
        for o in _OPEN.values():
            try:
                o.f.close()
            except OSError:
                pass
        _OPEN.clear()


atexit.register(close_all)


class JsonlAuditLog:
    def __init__(self, path: str | os.PathLike | None = None):
        self._path = Path(path or os.environ.get("CLAIMGUARD_AUDIT_PATH") or DEFAULT_PATH)

    def _iter_rows(self) -> Iterator[dict]:
        if not self._path.exists():
            return
        with self._path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)

    def _last(self) -> tuple[int, str]:
        if not self._path.exists():
            return 0, GENESIS
        with self._path.open("rb") as f:
            return _tail(f)

    def append(self, type: str, claim_id: Optional[str], details: dict) -> AuditEvent:
        with _THREAD_LOCK, _file_lock(self._path):
            o = _get_open(self._path)
            if os.fstat(o.f.fileno()).st_size != o.size:  # first use, or changed from outside
                o.seq, o.hash = _tail(o.f)
            payload = {"seq": o.seq + 1,
                       "ts": datetime.now(timezone.utc).isoformat(),
                       "type": type, "claim_id": claim_id,
                       "details": json.loads(json.dumps(details, default=str))}
            row = {**payload, "prev_hash": o.hash, "hash": _digest(o.hash, payload)}
            o.f.write((json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))
            o.f.flush()  # visible to readers; no fsync (see note on durability)
            o.size = os.fstat(o.f.fileno()).st_size
            o.seq, o.hash = row["seq"], row["hash"]
            return AuditEvent(**row)

    def read(self, claim_id: Optional[str] = None) -> list[AuditEvent]:
        return [AuditEvent(**r) for r in self._iter_rows()
                if claim_id is None or r["claim_id"] == claim_id]

    def verify(self) -> tuple[bool, Optional[int]]:
        prev = GENESIS
        for i, r in enumerate(self._iter_rows(), start=1):
            payload = {k: r[k] for k in ("seq", "ts", "type", "claim_id", "details")}
            if r["seq"] != i or r["prev_hash"] != prev or r["hash"] != _digest(prev, payload):
                return False, i
            prev = r["hash"]
        return True, None
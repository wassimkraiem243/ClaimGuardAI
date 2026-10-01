"""Choose the audit backend from configuration. Default 'file' keeps the old behaviour.
CLAIMGUARD_AUDIT_BACKEND=postgres uses PostgreSQL (see CLAIMGUARD_DATABASE_URL)."""
import os

from app.domain.audit import AuditLog


def get_audit_log() -> AuditLog:
    backend = os.environ.get("CLAIMGUARD_AUDIT_BACKEND", "file").lower()
    if backend == "postgres":
        from app.infrastructure.audit.postgres_audit import PostgresAuditLog
        return PostgresAuditLog()
    if backend == "file":
        from app.infrastructure.audit.jsonl_audit import JsonlAuditLog
        return JsonlAuditLog()
    raise ValueError(f"Unknown CLAIMGUARD_AUDIT_BACKEND: {backend!r} (use 'file' or 'postgres')")
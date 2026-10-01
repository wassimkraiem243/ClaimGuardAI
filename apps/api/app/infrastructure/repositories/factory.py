"""Claim persistence is enabled only with the PostgreSQL backend; otherwise the app stays stateless."""
import os
from typing import Optional

from app.domain.claim_repository import ClaimRepository


def get_claim_repository() -> Optional[ClaimRepository]:
    if os.environ.get("CLAIMGUARD_AUDIT_BACKEND", "file").lower() == "postgres":
        from app.infrastructure.repositories.postgres_claims import PostgresClaimRepository
        return PostgresClaimRepository()
    return None
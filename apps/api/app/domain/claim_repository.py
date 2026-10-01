from typing import Optional, Protocol

from app.domain.claim_package import ClaimPackage
from app.domain.finding import ValidationFinding


class ClaimConflict(Exception):
    """Same claim_id already stored with different content."""

    def __init__(self, claim_id: str):
        super().__init__(f"Claim {claim_id} already exists with different content")
        self.claim_id = claim_id


class ClaimRepository(Protocol):
    """Port: persistence of normalized claims and their findings."""

    def save(self, claim: ClaimPackage, file_sha256: str, received_at: str) -> bool: ...
    def save_findings(self, claim_id: str, findings: list[ValidationFinding]) -> None: ...
    def get(self, claim_id: str) -> Optional[dict]: ...
    def findings_for(self, claim_id: str) -> list[dict]: ...
    def prior_services(self, claims: list[ClaimPackage]) -> dict[tuple, set[str]]: ...
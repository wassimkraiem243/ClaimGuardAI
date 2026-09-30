from typing import Protocol
from app.domain.claim_package import ClaimPackage


class ClaimParser(Protocol):
    """Port: any input format (CSV, FHIR...) implements this."""

    def parse(self, raw: bytes) -> list[ClaimPackage]: ...
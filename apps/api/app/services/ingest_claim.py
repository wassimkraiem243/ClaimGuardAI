from app.domain.claim_package import ClaimPackage
from app.domain.ports import ClaimParser


class IngestClaim:
    """Use case: raw bytes -> normalized ClaimPackages. Knows nothing about HTTP or CSV."""

    def __init__(self, parser: ClaimParser):
        self._parser = parser

    def execute(self, raw: bytes) -> list[ClaimPackage]:
        return self._parser.parse(raw)
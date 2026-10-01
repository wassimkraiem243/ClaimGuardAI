from app.domain.claim_package import ClaimPackage
from app.domain.ports import ClaimParser
from app.infrastructure.parsers.csv_parser import CsvClaimParser
from app.infrastructure.parsers.fhir_parser import FhirClaimParser


def _select_parser(filename: str | None) -> ClaimParser:
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return CsvClaimParser()
    if name.endswith(".json"):
        return FhirClaimParser()
    raise ValueError("Unsupported file type: upload a .csv or a .json (FHIR Bundle)")


class IngestClaim:
    """Use case: raw bytes -> normalized ClaimPackages. Knows nothing about HTTP."""

    def __init__(self, parser: ClaimParser):
        self._parser = parser

    def execute(self, raw: bytes) -> list[ClaimPackage]:
        return self._parser.parse(raw)


def ingest_upload(filename: str | None, raw: bytes) -> list[ClaimPackage]:
    return IngestClaim(_select_parser(filename)).execute(raw)
import json

from app.domain.normalized_claim import NormalizedClaim
from app.domain.ports import ClaimParser
from app.infrastructure.parsers.csv_parser import CsvClaimParser
from app.infrastructure.parsers.fhir_parser import FhirClaimParser
from app.infrastructure.parsers.jsonl_parser import JsonlEnvelopeParser
from app.infrastructure.parsers.pack_csv_zip_parser import PackCsvZipParser
from app.infrastructure.parsers.pack_fhir_parser import PackFhirBundleParser


class _LegacyCsvParser:
    def parse(self, raw: bytes) -> list[NormalizedClaim]:
        return CsvClaimParser().parse_normalized(raw)


class _LegacyFhirParser:
    def parse(self, raw: bytes) -> list[NormalizedClaim]:
        return FhirClaimParser().parse_normalized(raw)


def _select_parser(filename: str | None, raw: bytes) -> ClaimParser:
    name = (filename or "").lower()
    if name.endswith(".jsonl"):
        return JsonlEnvelopeParser()
    if name.endswith(".zip"):
        return PackCsvZipParser()
    if name.endswith(".json"):
        try:
            obj = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Invalid JSON file")
        if isinstance(obj, dict) and obj.get("schema_version") == "1.0.0" and "lines" in obj:
            return PackFhirBundleParser()
        if isinstance(obj, dict) and obj.get("resourceType") == "Bundle":
            if b"claimguard.example" in raw:
                return PackFhirBundleParser()
            return _LegacyFhirParser()
        return PackFhirBundleParser()
    if name.endswith(".csv"):
        return _LegacyCsvParser()
    raise ValueError(
        "Unsupported file type: upload .jsonl (pack), .zip (pack csv/), "
        ".json (envelope or FHIR Bundle), or legacy .csv"
    )


class IngestClaim:
    """Use case: raw bytes -> normalized pack envelopes."""

    def __init__(self, parser: ClaimParser):
        self._parser = parser

    def execute(self, raw: bytes) -> list[NormalizedClaim]:
        return self._parser.parse(raw)


def ingest_upload(filename: str | None, raw: bytes) -> list[NormalizedClaim]:
    return IngestClaim(_select_parser(filename, raw)).execute(raw)

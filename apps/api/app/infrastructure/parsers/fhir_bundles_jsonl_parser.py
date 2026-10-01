"""JSONL with one FHIR Bundle per line (pack fhir_bundles.jsonl)."""
import json

from app.domain.claim_package import IngestionRejected
from app.domain.normalized_claim import NormalizedClaim
from app.infrastructure.parsers.pack_fhir_parser import PackFhirBundleParser


class FhirBundlesJsonlParser:
    def parse(self, raw: bytes) -> list[NormalizedClaim]:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise IngestionRejected("File is not valid UTF-8 text")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            raise IngestionRejected("JSONL file is empty")
        bundle_parser = PackFhirBundleParser()
        out: list[NormalizedClaim] = []
        for n, line in enumerate(lines, start=1):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                raise IngestionRejected("Invalid JSON on line", field_path=f"line {n}")
            if not isinstance(obj, dict) or obj.get("resourceType") != "Bundle":
                raise IngestionRejected(
                    "Each line must be a FHIR Bundle (resourceType Bundle)",
                    field_path=f"line {n}",
                )
            (norm,) = bundle_parser.parse(json.dumps(obj).encode("utf-8"))
            out.append(norm)
        return out

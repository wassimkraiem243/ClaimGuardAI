"""Pack relational CSV export (claims + lines + coverage + authorizations + attachments) as a zip."""
import csv
import io
import zipfile
from typing import Any

from app.domain.claim_package import IngestionRejected
from app.domain.normalized_claim import NormalizedClaim
from app.mappers.envelope import validate_and_seal

_NUMERIC = {
    "lines": {"quantity", "unit_price", "net_amount"},
    "authorizations": {"max_quantity"},
    "coverage": set(),
    "attachments": set(),
}


def _read_csv(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def _number(v: str | None):
    if v is None or v == "":
        return None
    n = float(v)
    return int(n) if n.is_integer() else n


def _convert_tables(tables: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    claims = tables.get("claims")
    if not claims:
        raise IngestionRejected("Zip must contain claims.csv")
    by_id = {c["claim_id"]: dict(c) for c in claims}
    for c in by_id.values():
        for k, v in list(c.items()):
            if v == "":
                c[k] = None
        c["total_amount"] = _number(c.get("total_amount")) if c.get("total_amount") is not None else None
        c["coverage"] = None
        c["lines"] = []
        c["authorizations"] = []
        c["attachments"] = []

    for name in ("coverage", "lines", "authorizations", "attachments"):
        for row in tables.get(name, []):
            cid = row.pop("claim_id", None)
            if cid not in by_id:
                raise IngestionRejected(f"{name}.csv references unknown claim_id", claim_id=cid)
            for k, v in list(row.items()):
                if k in _NUMERIC.get(name, set()):
                    row[k] = _number(v)
                elif v == "":
                    row[k] = None
            if name == "coverage":
                by_id[cid][name] = row
            else:
                by_id[cid][name].append(row)

    for cid, c in by_id.items():
        if c["coverage"] is None:
            raise IngestionRejected("Missing coverage row", claim_id=cid)
    return list(by_id.values())


class PackCsvZipParser:
    def parse(self, raw: bytes) -> list[NormalizedClaim]:
        try:
            zf = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile:
            raise IngestionRejected("Expected a zip containing pack CSV files")
        tables: dict[str, list[dict[str, Any]]] = {}
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/").split("/")[-1]
            stem = name.replace(".csv", "")
            if stem not in ("claims", "coverage", "lines", "authorizations", "attachments"):
                continue
            text = zf.read(info).decode("utf-8-sig")
            tables[stem] = _read_csv(text)
        if "claims" not in tables:
            raise IngestionRejected("Zip must include claims.csv (and related csv/)")
        envelopes = _convert_tables(tables)
        return [
            NormalizedClaim(
                envelope=validate_and_seal(env, claim_id=env["claim_id"]),
                source="PACK_CSV",
            )
            for env in envelopes
        ]

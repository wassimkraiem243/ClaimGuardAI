"""CSV adapter: one row per claim line, rows grouped by claim_id."""
import csv
import io
from collections import OrderedDict

from app.domain.claim_package import (ClaimLine, ClaimPackage, Coverage, Diagnosis, Encounter,
                                      IngestionRejected, Patient, Provider)
from app.mappers.normalizer import norm_code, norm_date, norm_gender, norm_number, norm_text

REQUIRED = ["claim_id", "patient_id", "encounter_id", "policy_id", "provider_id",
            "line_no", "procedure_code", "quantity", "amount"]


class CsvClaimParser:
    def parse(self, raw: bytes) -> list[ClaimPackage]:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise IngestionRejected("File is not valid UTF-8 text")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise IngestionRejected("Empty CSV or missing header row")
        header = [h.strip().lower() for h in reader.fieldnames]
        reader.fieldnames = header
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            raise IngestionRejected(f"Missing required columns: {missing}", field_path="header")

        groups: "OrderedDict[str, list[dict]]" = OrderedDict()
        for n, row in enumerate(reader, start=2):  # row 1 = header
            cid = norm_text(row.get("claim_id"))
            if not cid:
                raise IngestionRejected("Row without claim_id", field_path=f"row {n}.claim_id")
            row["_row"] = n
            groups.setdefault(cid, []).append(row)
        if not groups:
            raise IngestionRejected("CSV has a header but no data rows")
        return [self._build(cid, rows) for cid, rows in groups.items()]

    def _build(self, cid: str, rows: list[dict]) -> ClaimPackage:
        warnings: list[str] = []
        first = rows[0]

        def req(row, col):
            v = norm_text(row.get(col))
            if v is None:
                raise IngestionRejected(f"Required value empty: {col}",
                                        field_path=f"row {row['_row']}.{col}", claim_id=cid)
            return v

        def date(row, col):
            try:
                d = norm_date(row.get(col))
            except ValueError as e:
                raise IngestionRejected(str(e), field_path=f"row {row['_row']}.{col}", claim_id=cid)
            if d is None and row is first and col != "service_date":
                warnings.append(f"{col} missing")
            return d

        # Header-level entities must be identical across the claim's rows.
        for col in ("patient_id", "encounter_id", "policy_id", "provider_id"):
            values = {norm_text(r.get(col)) for r in rows}
            if len(values) > 1:
                raise IngestionRejected(f"Inconsistent {col} across lines: {sorted(map(str, values))}",
                                        field_path=col, claim_id=cid)

        lines, seen = [], set()
        for r in rows:
            try:
                line_no = int(req(r, "line_no"))
                qty = norm_number(req(r, "quantity"))
                amt = norm_number(req(r, "amount"))
            except ValueError:
                raise IngestionRejected("Non-numeric line_no/quantity/amount",
                                        field_path=f"row {r['_row']}", claim_id=cid)
            if line_no in seen:
                raise IngestionRejected(f"Duplicate line_no {line_no}", field_path=f"row {r['_row']}", claim_id=cid)
            seen.add(line_no)
            cur = norm_code(r.get("currency"))
            if cur is None:
                warnings.append(f"line {line_no}: currency missing")
            if not norm_text(r.get("authorization_id")):
                warnings.append(f"line {line_no}: authorization_id missing")
            lines.append(ClaimLine(line_no=line_no, procedure_code=norm_code(req(r, "procedure_code")),
                                   quantity=qty, amount=amt, currency=cur,
                                   service_date=date(r, "service_date"),
                                   authorization_id=norm_text(r.get("authorization_id"))))

        codes = [c for c in (norm_code(x) for x in (first.get("diagnosis_codes") or "").split(";")) if c]
        if not codes:
            warnings.append("no diagnosis codes")
        return ClaimPackage(
            claim_id=cid, source="CSV",
            patient=Patient(id=req(first, "patient_id"), birth_date=date(first, "birth_date"),
                            gender=norm_gender(first.get("gender"))),
            encounter=Encounter(id=req(first, "encounter_id"), start=date(first, "encounter_start"),
                                end=date(first, "encounter_end")),
            coverage=Coverage(policy_id=req(first, "policy_id"), payer_id=norm_text(first.get("payer_id")),
                              start=date(first, "coverage_start"), end=date(first, "coverage_end")),
            provider=Provider(id=req(first, "provider_id"), npi=norm_text(first.get("provider_npi"))),
            diagnoses=[Diagnosis(code=c, primary=(i == 0)) for i, c in enumerate(codes)],
            lines=sorted(lines, key=lambda l: l.line_no),
            ingestion_warnings=warnings,
        )
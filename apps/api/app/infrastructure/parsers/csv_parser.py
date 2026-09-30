"""CSV adapter: one row per claim line, rows grouped by claim_id."""
import csv
import io
from collections import OrderedDict

from app.domain.claim_package import (ClaimLine, ClaimPackage, Coverage, Diagnosis, Encounter,
                                      IngestionRejected, Patient, Provider)
from app.mappers.normalizer import norm_code, norm_date, norm_number, norm_text

REQUIRED = ["claim_id", "patient_id", "encounter_id", "policy_id", "provider_id",
            "line_no", "procedure_code", "quantity", "amount"]
IDENTITY_COLS = ("patient_id", "encounter_id", "policy_id", "provider_id")


def _codes(value):
    codes = tuple(c for c in (norm_code(x) for x in (value or "").split(";")) if c)
    return codes or None


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

        def reject(msg, row=None, col=None):
            path = f"row {row['_row']}" + (f".{col}" if col else "") if row else col
            raise IngestionRejected(msg, field_path=path, claim_id=cid)

        def req(row, col):
            v = norm_text(row.get(col))
            if v is None:
                reject(f"Required value empty: {col}", row, col)
            return v

        def head(col, conv=norm_text):
            """Claim-level value repeated on every row: take the first non-empty one
            (a blank first row must not hide later rows) and reject real conflicts."""
            seen = []
            for r in rows:
                try:
                    v = conv(r.get(col))
                except ValueError as e:
                    reject(str(e), r, col)
                if v is not None and v not in seen:
                    seen.append(v)
            if len(seen) > 1:
                reject(f"Conflicting {col} across lines: {[s for s in seen]}", col=col)
            return seen[0] if seen else None

        def number(row, col):
            v = req(row, col)
            try:
                return norm_number(v)
            except ValueError:
                reject(f"{col} is not a valid number: {v!r}", row, col)

        for col in IDENTITY_COLS:  # identity fields are strict: any difference or blank is a reject
            values = {norm_text(r.get(col)) for r in rows}
            if len(values) > 1:
                reject(f"Inconsistent {col} across lines: {sorted(map(str, values))}", col=col)

        lines, seen_nos = [], set()
        for r in rows:
            v = req(r, "line_no")
            try:
                line_no = int(v)
            except ValueError:
                reject(f"line_no must be an integer: {v!r}", r, "line_no")
            if line_no < 1:
                reject(f"line_no must be >= 1: {line_no}", r, "line_no")
            if line_no in seen_nos:
                reject(f"Duplicate line_no {line_no}", r)
            seen_nos.add(line_no)
            qty, amt = number(r, "quantity"), number(r, "amount")
            cur = norm_code(r.get("currency"))
            if cur is None:
                warnings.append(f"line {line_no}: currency missing")
            if not norm_text(r.get("authorization_id")):
                warnings.append(f"line {line_no}: authorization_id missing")
            try:
                svc = norm_date(r.get("service_date"))
            except ValueError as e:
                reject(str(e), r, "service_date")
            if svc is None:
                warnings.append(f"line {line_no}: service_date missing")
            lines.append(ClaimLine(line_no=line_no, procedure_code=norm_code(req(r, "procedure_code")),
                                   quantity=qty, amount=amt, currency=cur, service_date=svc,
                                   authorization_id=norm_text(r.get("authorization_id"))))

        dates = {col: head(col, norm_date) for col in
                 ("birth_date", "encounter_start", "encounter_end", "coverage_start", "coverage_end")}
        warnings += [f"{col} missing" for col, v in dates.items() if v is None]
        codes = head("diagnosis_codes", _codes) or ()
        if not codes:
            warnings.append("no diagnosis codes")
        first = rows[0]
        return ClaimPackage(
            claim_id=cid, source="CSV",
            patient=Patient(id=req(first, "patient_id"), birth_date=dates["birth_date"],
                            gender=head("gender")),
            encounter=Encounter(id=req(first, "encounter_id"), start=dates["encounter_start"],
                                end=dates["encounter_end"]),
            coverage=Coverage(policy_id=req(first, "policy_id"), payer_id=head("payer_id"),
                              start=dates["coverage_start"], end=dates["coverage_end"]),
            provider=Provider(id=req(first, "provider_id"), npi=head("provider_npi")),
            diagnoses=[Diagnosis(code=c, primary=(i == 0)) for i, c in enumerate(codes)],
            lines=sorted(lines, key=lambda l: l.line_no),
            ingestion_warnings=warnings,
        )
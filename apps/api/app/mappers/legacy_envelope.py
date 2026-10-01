"""Map legacy ClaimPackage (CSV/FHIR demo files) to a teaching envelope where possible."""
from app.domain.claim_package import ClaimPackage
from app.domain.normalized_claim import NormalizedClaim
from app.mappers.envelope import validate_and_seal
from app.mappers.normalizer import norm_date


def claim_package_to_envelope(pkg: ClaimPackage, source: str) -> NormalizedClaim:
    warnings = list(pkg.ingestion_warnings)
    primary_dx = pkg.diagnoses[0].code if pkg.diagnoses else None
    currency = pkg.lines[0].currency if pkg.lines else None
    total = round(sum(l.amount for l in pkg.lines), 2)
    member_id = f"MEM-{pkg.patient.id}" if pkg.patient.id else None
    envelope = {
        "schema_version": "1.0.0",
        "claim_id": pkg.claim_id,
        "invoice_number": f"INV-{pkg.claim_id}",
        "patient_id": pkg.patient.id,
        "member_id": member_id,
        "provider_id": pkg.provider.id,
        "payer_id": pkg.coverage.payer_id or "UNKNOWN-PAYER",
        "policy_id": pkg.coverage.policy_id,
        "diagnosis_code": primary_dx,
        "submission_date": norm_date(pkg.encounter.end or pkg.encounter.start) or "2026-01-01",
        "currency": currency or "USD",
        "total_amount": total,
        "coverage": {
            "coverage_id": f"COV-{pkg.claim_id}",
            "status": "active",
            "beneficiary_patient_id": pkg.patient.id,
            "member_id": member_id,
            "start_date": norm_date(pkg.coverage.start),
            "end_date": norm_date(pkg.coverage.end),
        },
        "lines": [
            {
                "line_id": f"L{ln.line_no}",
                "service_code": ln.procedure_code,
                "service_date": norm_date(ln.service_date),
                "modifier": None,
                "quantity": int(ln.quantity) if ln.quantity == int(ln.quantity) else ln.quantity,
                "unit_price": ln.amount / ln.quantity if ln.quantity else ln.amount,
                "net_amount": int(ln.amount) if ln.amount == int(ln.amount) else ln.amount,
                "authorization_id": ln.authorization_id,
            }
            for ln in pkg.lines
        ],
        "authorizations": [],
        "attachments": [],
        "notes": "Synthetic claim. No real patient or payer information.",
    }
    if source == "FHIR_LEGACY":
        warnings.append("legacy FHIR demo mapping; use pack FHIR bundles for evaluation")
    else:
        warnings.append("legacy flat CSV mapping; use pack JSONL or CSV zip for evaluation")
    envelope = validate_and_seal(envelope, claim_id=pkg.claim_id)
    return NormalizedClaim(envelope=envelope, source=source, ingestion_warnings=warnings)

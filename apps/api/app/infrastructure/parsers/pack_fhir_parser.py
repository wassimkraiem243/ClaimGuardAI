"""Teaching FHIR collection Bundle → pack claim envelope (doc 11 subset)."""
import json
from typing import Any, Optional

from app.domain.claim_package import IngestionRejected
from app.domain.normalized_claim import NormalizedClaim
from app.mappers.envelope import validate_and_seal
from app.mappers.normalizer import norm_date, norm_text

_LINE_AUTH_EXT = "https://claimguard.example/StructureDefinition/line-authorization-id"
_MEMBER_ID_SYSTEM = "https://claimguard.example/ids/member"
_INVOICE_SYSTEM = "https://claimguard.example/ids/invoice"
_DOC_STATUS = {"preliminary": "draft", "final": "final", "amended": "final", "entered-in-error": "draft"}


def _rej(reason, path=None, cid=None):
    return IngestionRejected(reason, field_path=path, claim_id=cid)


def _index_bundle(bundle: dict) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for e in bundle.get("entry") or []:
        if not isinstance(e, dict):
            continue
        res = e.get("resource")
        if not isinstance(res, dict):
            continue
        if res.get("id") and res.get("resourceType"):
            index[f"{res['resourceType']}/{res['id']}"] = res
        if isinstance(e.get("fullUrl"), str):
            index[e["fullUrl"]] = res
            parts = e["fullUrl"].rstrip("/").split("/")
            if len(parts) >= 2:
                index["/".join(parts[-2:])] = res
    return index


def _ref_key(ref: str) -> str:
    if ref.startswith("http"):
        return "/".join(ref.rstrip("/").split("/")[-2:])
    return ref.lstrip("#")


def _resolve(ref: dict | None, index: dict, types: set[str], path: str, cid: str) -> dict:
    r = ref.get("reference") if isinstance(ref, dict) else None
    if not isinstance(r, str):
        raise _rej("Missing reference", path, cid)
    res = index.get(r) or index.get(_ref_key(r))
    if res is None or res.get("resourceType") not in types:
        raise _rej(f"Dangling or wrong-type reference: {r}", path, cid)
    return res


def _first_code(concept: dict | None) -> Optional[str]:
    coding = (concept or {}).get("coding") or []
    if not coding:
        return None
    return norm_text(coding[0].get("code"))


def _org_id(org: dict) -> str:
    if not norm_text(org.get("id")):
        raise IngestionRejected("Organization without id")
    return str(org["id"])


def _attachment_text(doc: dict) -> str:
    for block in doc.get("content") or []:
        att = block.get("attachment") or {}
        data = att.get("data")
        if isinstance(data, str):
            try:
                return base64.b64decode(data).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                return ""
    return ""


def _doc_status(doc: dict) -> str:
    raw = str(doc.get("docStatus") or doc.get("status") or "unknown").lower()
    return _DOC_STATUS.get(raw, raw)


def bundle_to_envelope(bundle: dict) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    if bundle.get("resourceType") != "Bundle":
        raise IngestionRejected("Expected a FHIR Bundle", field_path="resourceType")
    index = _index_bundle(bundle)
    seen_claim: set[str] = set()
    claims: list[dict] = []
    for r in index.values():
        if not isinstance(r, dict) or r.get("resourceType") != "Claim":
            continue
        rid = str(r.get("id") or "")
        if rid in seen_claim:
            continue
        seen_claim.add(rid)
        claims.append(r)
    if len(claims) != 1:
        raise IngestionRejected("Pack FHIR bundle must contain exactly one Claim resource", field_path="entry")
    claim = claims[0]
    cid = norm_text(claim.get("id"))
    if not cid:
        raise _rej("Claim without id", "Claim.id")

    pat = _resolve(claim.get("patient"), index, {"Patient"}, "Claim.patient", cid)
    patient_id = str(pat["id"])
    member_id = None
    for ident in pat.get("identifier") or []:
        if _MEMBER_ID_SYSTEM in str(ident.get("system", "")):
            member_id = norm_text(ident.get("value"))
            break

    prov = _resolve(claim.get("provider"), index, {"Organization"}, "Claim.provider", cid)
    provider_id = _org_id(prov)
    payer = _resolve(claim.get("insurer"), index, {"Organization"}, "Claim.insurer", cid)
    payer_id = _org_id(payer)

    insurance = claim.get("insurance")
    if not isinstance(insurance, list) or not insurance:
        raise _rej("Claim without insurance", "Claim.insurance", cid)
    ins = next((i for i in insurance if isinstance(i, dict) and i.get("focal")), insurance[0])
    cov_res = _resolve(ins.get("coverage"), index, {"Coverage"}, "Claim.insurance[0].coverage", cid)
    policy_id = None
    for cl in cov_res.get("class") or []:
        coding = ((cl.get("type") or {}).get("coding") or [{}])[0]
        if str(coding.get("code", "")).lower() == "plan":
            policy_id = norm_text(cl.get("value"))
            break
    if not policy_id:
        warnings.append("policy_id inferred from coverage.class missing; using coverage id")
        policy_id = str(cov_res.get("id") or "")
    if not member_id:
        member_id = norm_text(cov_res.get("subscriberId"))
    if not member_id:
        warnings.append("member_id missing")

    coverage = {
        "coverage_id": str(cov_res["id"]),
        "status": norm_text(cov_res.get("status")),
        "beneficiary_patient_id": patient_id,
        "member_id": member_id,
        "start_date": norm_date((cov_res.get("period") or {}).get("start")),
        "end_date": norm_date((cov_res.get("period") or {}).get("end")),
    }

    invoice_number = None
    for ident in claim.get("identifier") or []:
        if _INVOICE_SYSTEM in str(ident.get("system", "")):
            invoice_number = norm_text(ident.get("value"))
            break
    if invoice_number is None:
        warnings.append("invoice_number missing")

    diagnosis_code = None
    diags = sorted(claim.get("diagnosis") or [], key=lambda d: d.get("sequence", 0))
    if diags:
        diagnosis_code = _first_code(diags[0].get("diagnosisCodeableConcept"))
    if diagnosis_code is None:
        warnings.append("diagnosis_code missing")

    created = norm_date(str(claim.get("created", ""))[:10]) if claim.get("created") else None
    if created is None:
        raise _rej("Claim.created missing or invalid", "Claim.created", cid)

    total = claim.get("total") or {}
    currency = norm_text(total.get("currency"))
    total_amount = total.get("value")
    if isinstance(total_amount, bool) or not isinstance(total_amount, (int, float)):
        total_amount = None
    if currency is None:
        warnings.append("currency missing")

    pre_auth = ins.get("preAuthRef")
    default_auth = norm_text(pre_auth[0]) if isinstance(pre_auth, list) and pre_auth else None

    lines: list[dict] = []
    for it in sorted(claim.get("item") or [], key=lambda x: x.get("sequence", 0)):
        seq = it.get("sequence")
        if not isinstance(seq, int):
            raise _rej("Item without integer sequence", "Claim.item.sequence", cid)
        auth_id = default_auth
        for ext in it.get("extension") or []:
            if ext.get("url") == _LINE_AUTH_EXT:
                auth_id = norm_text(ext.get("valueString"))
        svc = _first_code(it.get("productOrService"))
        qty = (it.get("quantity") or {}).get("value")
        unit = (it.get("unitPrice") or {}).get("value")
        net = (it.get("net") or {}).get("value")
        for label, val in (("quantity", qty), ("unit_price", unit), ("net_amount", net)):
            if isinstance(val, bool) or (val is not None and not isinstance(val, (int, float))):
                raise _rej(f"Invalid numeric {label}", f"Claim.item[{seq}].{label}", cid)
        lines.append({
            "line_id": f"L{seq}",
            "service_code": svc,
            "service_date": norm_date(it.get("servicedDate")),
            "modifier": None,
            "quantity": int(qty) if isinstance(qty, float) and qty.is_integer() else qty,
            "unit_price": int(unit) if isinstance(unit, float) and unit.is_integer() else unit,
            "net_amount": int(net) if isinstance(net, float) and net.is_integer() else net,
            "authorization_id": auth_id,
        })

    if not lines:
        raise _rej("Claim without items", "Claim.item", cid)

    authorizations: list[dict] = []
    if default_auth:
        authorizations.append({
            "authorization_id": default_auth,
            "patient_id": patient_id,
            "service_code": lines[0].get("service_code"),
            "status": "approved",
            "valid_from": None,
            "valid_to": None,
            "max_quantity": None,
        })
        warnings.append("authorization dates/limits not in FHIR; sidecar fields set to null")

    attachments: list[dict] = []
    for si in claim.get("supportingInfo") or []:
        ref = (si.get("valueReference") or {}).get("reference")
        if not isinstance(ref, str):
            continue
        doc = index.get(ref) or index.get(_ref_key(ref))
        if not isinstance(doc, dict) or doc.get("resourceType") != "DocumentReference":
            warnings.append(f"unsupported supportingInfo reference: {ref}")
            continue
        doc_id = str(doc.get("id") or "")
        att_type = _first_code(doc.get("type")) or "document"
        ctx = doc.get("context") or {}
        period = ctx.get("period") or {}
        attachments.append({
            "attachment_id": doc_id,
            "type": att_type,
            "patient_id": patient_id,
            "service_code": lines[0].get("service_code"),
            "service_date": norm_date(period.get("start") or period.get("end")),
            "document_status": _doc_status(doc),
            "text": _attachment_text(doc),
        })

    envelope: dict[str, Any] = {
        "schema_version": "1.0.0",
        "claim_id": cid,
        "invoice_number": invoice_number,
        "patient_id": patient_id,
        "member_id": member_id,
        "provider_id": provider_id,
        "payer_id": payer_id,
        "policy_id": policy_id,
        "diagnosis_code": diagnosis_code,
        "submission_date": created,
        "currency": currency or "SAR",
        "total_amount": total_amount,
        "coverage": coverage,
        "lines": lines,
        "authorizations": authorizations,
        "attachments": attachments,
        "notes": "Synthetic claim. No real patient or payer information.",
    }
    return envelope, warnings


class PackFhirBundleParser:
    def parse(self, raw: bytes) -> list[NormalizedClaim]:
        try:
            bundle = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise IngestionRejected("Invalid JSON")
        if not isinstance(bundle, dict):
            raise IngestionRejected("Expected a JSON object")
        if bundle.get("schema_version") == "1.0.0" and "lines" in bundle:
            envelope = validate_and_seal(bundle, claim_id=bundle.get("claim_id"))
            return [NormalizedClaim(envelope=envelope, source="JSONL")]
        envelope, warnings = bundle_to_envelope(bundle)
        envelope = validate_and_seal(envelope, claim_id=envelope.get("claim_id"))
        return [NormalizedClaim(envelope=envelope, source="FHIR_PACK", ingestion_warnings=warnings)]

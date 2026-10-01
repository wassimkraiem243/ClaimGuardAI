"""FHIR R4 adapter: Bundle JSON -> one ClaimPackage per Claim resource."""
import json
import math

from app.domain.claim_package import (ClaimLine, ClaimPackage, Coverage, Diagnosis, Encounter,
                                      IngestionRejected, Patient, Provider)
from app.mappers.normalizer import norm_code, norm_date, norm_text

_GENDER = {"male": "M", "female": "F", "other": "O", "unknown": "U"}
_PROVIDER_TYPES = {"Practitioner", "Organization", "PractitionerRole"}


class _NonFinite(Exception):
    pass


def _reject_constant(name):  # json.loads would otherwise accept NaN / Infinity
    raise _NonFinite(f"Non-finite number in JSON: {name}")


def _rej(reason, path=None, cid=None):
    return IngestionRejected(reason, field_path=path, claim_id=cid)


def _date(value, path, cid):
    if value is None:
        return None
    if not isinstance(value, str):
        raise _rej("Invalid date value", path, cid)
    try:
        return norm_date(value[:10])  # FHIR dateTime -> keep the date part
    except ValueError as e:
        raise _rej(str(e), path, cid)


def _num(value, path, cid):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _rej("Expected a number", path, cid)
    f = float(value)
    if not math.isfinite(f):  # 1e999 parses to inf
        raise _rej("Number is not finite", path, cid)
    return f


def _first_code(concept, path, cid):
    coding = (concept or {}).get("coding")
    if not isinstance(coding, list) or not coding or not norm_code(coding[0].get("code")):
        raise _rej("Missing coding.code", path, cid)
    return norm_code(coding[0]["code"])


def _is_principal(diag: dict) -> bool:
    return any(str(c.get("code", "")).lower() == "principal"
               for t in (diag.get("type") or []) for c in (t.get("coding") or []))


class FhirClaimParser:
    def parse(self, raw: bytes) -> list[ClaimPackage]:
        try:
            bundle = json.loads(raw.decode("utf-8-sig"), parse_constant=_reject_constant)
        except _NonFinite as e:
            raise IngestionRejected(str(e))
        except RecursionError:
            raise IngestionRejected("JSON is nested too deeply")
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise IngestionRejected("Invalid JSON")
        if not isinstance(bundle, dict) or bundle.get("resourceType") != "Bundle":
            raise IngestionRejected("Expected a FHIR Bundle", field_path="resourceType")
        entries = bundle.get("entry")
        if not isinstance(entries, list) or not entries:
            raise IngestionRejected("Bundle has no entries", field_path="entry")

        index, claims = {}, []
        for i, e in enumerate(entries):
            res = e.get("resource") if isinstance(e, dict) else None
            if not isinstance(res, dict) or not isinstance(res.get("resourceType"), str):
                raise IngestionRejected("Entry without a valid resource", field_path=f"entry[{i}]")
            if res.get("id") is not None:
                index[f"{res['resourceType']}/{res['id']}"] = res
            if isinstance(e.get("fullUrl"), str):
                index[e["fullUrl"]] = res
            if res["resourceType"] == "Claim":
                claims.append(res)
        if not claims:
            raise IngestionRejected("Bundle contains no Claim resource", field_path="entry")
        out = []
        for c in claims:
            try:
                out.append(self._build(c, index))
            except IngestionRejected:
                raise
            except (KeyError, TypeError, AttributeError, ValueError, IndexError) as e:
                raise IngestionRejected(f"Malformed FHIR structure ({type(e).__name__})",
                                        claim_id=None if c.get("id") is None else str(c["id"]))
        return out

    @staticmethod
    def _resolve(ref, index, types, path, cid):
        r = ref.get("reference") if isinstance(ref, dict) else None
        if not isinstance(r, str):
            raise _rej("Missing reference", path, cid)
        res = index.get(r)
        if res is None and "/" in r:  # absolute URL -> try "Type/id"
            res = index.get("/".join(r.rstrip("/").split("/")[-2:]))
        if res is None or res["resourceType"] not in types:
            raise _rej(f"Dangling or wrong-type reference: {r}", path, cid)
        return res

    def _build(self, claim: dict, index: dict) -> ClaimPackage:
        cid = norm_text(claim.get("id"))
        if not cid:
            raise _rej("Claim without id", "Claim.id")
        w: list[str] = []
        if claim.get("use") not in (None, "claim"):
            w.append(f"Claim.use={claim.get('use')}: not a claim for payment")
        local = dict(index)
        for c in claim.get("contained") or []:  # contained resources, referenced as "#id"
            if isinstance(c, dict) and c.get("id") and isinstance(c.get("resourceType"), str):
                local[f"#{c['id']}"] = c
        res = lambda ref, types, path: self._resolve(ref, local, types, path, cid)  # noqa: E731

        pat = res(claim.get("patient"), {"Patient"}, "Claim.patient")
        insurance = claim.get("insurance")
        if not isinstance(insurance, list) or not insurance:
            raise _rej("Claim without insurance", "Claim.insurance", cid)
        ins = next((i for i in insurance if isinstance(i, dict) and i.get("focal") is True), insurance[0])
        cov = res(ins.get("coverage"), {"Coverage"}, "Claim.insurance[0].coverage")
        prov = res(claim.get("provider"), _PROVIDER_TYPES, "Claim.provider")
        items = claim.get("item")
        if not isinstance(items, list) or not items:
            raise _rej("Claim without items", "Claim.item", cid)
        enc_refs = [r for it in items if isinstance(it, dict)
                    for r in (it.get("encounter") or []) if isinstance(r, dict)]
        if not enc_refs:
            raise _rej("No claim item references an encounter", "Claim.item[].encounter", cid)
        encs = [res(r, {"Encounter"}, "Claim.item[].encounter[0]") for r in enc_refs]
        enc = encs[0]
        if any(e is not enc for e in encs[1:]):
            w.append("items reference several encounters; using the first")

        def rid(r, path):
            if not norm_text(r.get("id")):
                raise _rej("Resource without id", path, cid)
            return str(r["id"])

        gender = _GENDER.get(str(pat.get("gender", "")).lower())
        birth = _date(pat.get("birthDate"), "Patient.birthDate", cid)
        if gender is None:
            w.append("patient gender missing")
        if birth is None:
            w.append("birth_date missing")

        cov_period = cov.get("period") or {}
        ident = cov.get("identifier")
        policy = (ident[0].get("value") if isinstance(ident, list) and ident else None) \
            or cov.get("subscriberId") or cov.get("id")
        if not norm_text(policy):
            raise _rej("Coverage has no policy identifier", "Coverage.identifier", cid)
        payor = cov.get("payor")
        payer = None
        if isinstance(payor, list) and payor and isinstance(payor[0].get("reference"), str):
            payer = payor[0]["reference"].split("/")[-1]
        else:
            w.append("payer_id missing")
        coverage = Coverage(policy_id=str(policy), payer_id=payer,
                            start=_date(cov_period.get("start"), "Coverage.period.start", cid),
                            end=_date(cov_period.get("end"), "Coverage.period.end", cid))

        npi = next((i.get("value") for i in (prov.get("identifier") or [])
                    if "npi" in str(i.get("system", "")).lower()), None)
        if npi is None:
            w.append("provider npi missing")

        enc_period = enc.get("period") or {}
        encounter = Encounter(id=rid(enc, "Encounter.id"),
                              start=_date(enc_period.get("start"), "Encounter.period.start", cid),
                              end=_date(enc_period.get("end"), "Encounter.period.end", cid))

        diags = sorted(claim.get("diagnosis") or [], key=lambda d: d.get("sequence", 0))
        has_principal = any(_is_principal(d) for d in diags)
        diagnoses = [Diagnosis(code=_first_code(d.get("diagnosisCodeableConcept"),
                                                f"Claim.diagnosis[{i}]", cid),
                               primary=_is_principal(d) if has_principal else i == 0)
                     for i, d in enumerate(diags)]
        if not diagnoses:
            w.append("no diagnosis codes")

        pre = ins.get("preAuthRef")
        auth = norm_text(pre[0]) if isinstance(pre, list) and pre and isinstance(pre[0], str) else None

        lines, seen = [], set()
        for i, it in enumerate(items):
            p = f"Claim.item[{i}]"
            seq = it.get("sequence")
            if isinstance(seq, bool) or not isinstance(seq, int):
                raise _rej("Item without integer sequence", f"{p}.sequence", cid)
            if seq in seen:
                raise _rej(f"Duplicate item sequence {seq}", f"{p}.sequence", cid)
            seen.add(seq)
            net = it.get("net")
            if not isinstance(net, dict):
                raise _rej("Item without net amount", f"{p}.net", cid)
            currency = norm_code(net.get("currency"))
            if currency is None:
                w.append(f"line {seq}: currency missing")
            if auth is None:
                w.append(f"line {seq}: authorization_id missing")
            sdate = it.get("servicedDate") or (it.get("servicedPeriod") or {}).get("start")
            if sdate is None:
                w.append(f"line {seq}: service_date missing")
            lines.append(ClaimLine(
                line_no=seq, procedure_code=_first_code(it.get("productOrService"), f"{p}.productOrService", cid),
                quantity=_num((it.get("quantity") or {}).get("value"), f"{p}.quantity.value", cid),
                amount=_num(net.get("value"), f"{p}.net.value", cid), currency=currency,
                service_date=_date(sdate, f"{p}.servicedDate", cid), authorization_id=auth))

        return ClaimPackage(
            claim_id=cid, source="FHIR",
            patient=Patient(id=rid(pat, "Patient.id"), birth_date=birth, gender=gender),
            encounter=encounter, coverage=coverage,
            provider=Provider(id=rid(prov, "Claim.provider.id"), npi=norm_text(npi)),
            diagnoses=diagnoses, lines=sorted(lines, key=lambda l: l.line_no),
            ingestion_warnings=w)
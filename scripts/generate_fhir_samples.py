"""Generate synthetic FHIR R4 bundles (valid variants + deliberately broken ones) and a manifest.
Usage (repo root):  python scripts/generate_fhir_samples.py
Output: data/synthetic-claims/fhir/generated/*.json + manifest.json"""
import copy
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "synthetic-claims" / "fhir" / "generated"


def base(n="1"):
    """One complete, valid claim bundle (as a dict)."""
    p, e, c, pr, cl = f"P{n}", f"E{n}", f"COV-{n}", f"PRV-{n}", f"F{n}"
    return {"resourceType": "Bundle", "type": "collection", "entry": [
        {"resource": {"resourceType": "Patient", "id": p, "gender": "male", "birthDate": "1978-11-03"}},
        {"resource": {"resourceType": "Encounter", "id": e, "status": "finished",
                      "period": {"start": "2026-06-10T08:00:00Z", "end": "2026-06-10T08:45:00Z"}}},
        {"resource": {"resourceType": "Practitioner", "id": pr,
                      "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": "1999999999"}]}},
        {"resource": {"resourceType": "Coverage", "id": c, "status": "active",
                      "identifier": [{"value": f"POL-{n}"}], "payor": [{"reference": "Organization/PAYER-A"}],
                      "period": {"start": "2026-01-01", "end": "2026-12-31"}}},
        {"resource": {"resourceType": "Claim", "id": cl, "status": "active",
                      "patient": {"reference": f"Patient/{p}"}, "provider": {"reference": f"Practitioner/{pr}"},
                      "insurance": [{"sequence": 1, "focal": True, "coverage": {"reference": f"Coverage/{c}"},
                                     "preAuthRef": ["AUTH-9"]}],
                      "diagnosis": [{"sequence": 1, "diagnosisCodeableConcept": {"coding": [{"code": "i10"}]}}],
                      "item": [{"sequence": 1, "encounter": [{"reference": f"Encounter/{e}"}],
                                "productOrService": {"coding": [{"code": "99214"}]},
                                "servicedDate": "2026-06-10", "quantity": {"value": 1},
                                "net": {"value": 150, "currency": "USD"}}]}}]}


def claim(b):
    return next(e["resource"] for e in b["entry"] if e["resource"]["resourceType"] == "Claim")


def res(b, t):
    return next(e["resource"] for e in b["entry"] if e["resource"]["resourceType"] == t)


def v_urn():  # Synthea-style: urn:uuid fullUrl references
    b = base("2")
    for e in b["entry"]:
        r = e["resource"]
        e["fullUrl"] = f"urn:uuid:{r['resourceType'].lower()}-{r['id']}"
    c = claim(b)
    c["patient"] = {"reference": "urn:uuid:patient-P2"}
    c["provider"] = {"reference": "urn:uuid:practitioner-PRV-2"}
    c["insurance"][0]["coverage"] = {"reference": "urn:uuid:coverage-COV-2"}
    c["item"][0]["encounter"] = [{"reference": "urn:uuid:encounter-E2"}]
    return b


def v_contained():  # Patient contained inside the Claim
    b = base("3")
    pat = res(b, "Patient")
    b["entry"] = [e for e in b["entry"] if e["resource"]["resourceType"] != "Patient"]
    c = claim(b)
    c["contained"] = [pat]
    c["patient"] = {"reference": "#P3"}
    return b


def v_multi():  # two claims in one bundle
    b1, b2 = base("4"), base("5")
    b1["entry"] += b2["entry"]
    return b1


def v_minimal():  # optional data absent -> warnings, still accepted
    b = base("6")
    del res(b, "Patient")["gender"]
    del res(b, "Practitioner")["identifier"]
    del res(b, "Coverage")["payor"]
    c = claim(b)
    del c["insurance"][0]["preAuthRef"]
    del c["diagnosis"]
    return b


def v_principal_period():  # principal diagnosis not first + servicedPeriod
    b = base("7")
    c = claim(b)
    c["diagnosis"] = [
        {"sequence": 1, "diagnosisCodeableConcept": {"coding": [{"code": "r05"}]}},
        {"sequence": 2, "type": [{"coding": [{"code": "principal"}]}],
         "diagnosisCodeableConcept": {"coding": [{"code": "j45.0"}]}}]
    del c["item"][0]["servicedDate"]
    c["item"][0]["servicedPeriod"] = {"start": "2026-06-10T08:00:00Z", "end": "2026-06-10T08:45:00Z"}
    return b


def broken(mutator):
    b = base("9")
    mutator(b)
    return b


BROKEN = {
    "b04_dangling_encounter": (lambda b: claim(b)["item"][0].update(encounter=[{"reference": "Encounter/NOPE"}]),
                               "Claim.item[].encounter[0]"),
    "b05_net_is_string": (lambda b: claim(b)["item"][0].update(net="150"), "Claim.item[0].net"),
    "b06_no_items": (lambda b: claim(b).pop("item"), "Claim.item"),
    "b07_duplicate_sequence": (lambda b: claim(b)["item"].append(copy.deepcopy(claim(b)["item"][0])),
                               "Claim.item[1].sequence"),
    "b08_bad_date": (lambda b: res(b, "Patient").update(birthDate="not-a-date"), "Patient.birthDate"),
    "b09_no_insurance": (lambda b: claim(b).pop("insurance"), "Claim.insurance"),
    "b10_wrong_ref_type": (lambda b: claim(b).update(patient={"reference": "Practitioner/PRV-9"}), "Claim.patient"),
}


def write(name, content, raw=False):
    (OUT / f"{name}.json").write_bytes(content if raw else json.dumps(content, indent=2).encode())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = {}
    valid = {"v01_basic": (base("1"), 1), "v02_urn_uuid": (v_urn(), 1), "v03_contained": (v_contained(), 1),
             "v04_multi_claim": (v_multi(), 2), "v05_minimal_optional": (v_minimal(), 1),
             "v06_principal_servicedperiod": (v_principal_period(), 1)}
    for name, (b, n) in valid.items():
        write(name, b)
        m[f"{name}.json"] = {"expect": "ok", "claims": n}
    for name, (mut, path) in BROKEN.items():
        write(name, broken(mut))
        m[f"{name}.json"] = {"expect": "rejected", "field_path": path}
    for name, raw in {"b01_not_json": b"this is not json", "b02_not_a_bundle": b'{"resourceType":"Patient","id":"x"}',
                      "b03_empty_bundle": b'{"resourceType":"Bundle","entry":[]}'}.items():
        write(name, raw, raw=True)
        m[f"{name}.json"] = {"expect": "rejected"}
    (OUT / "manifest.json").write_text(json.dumps(m, indent=2))
    print(f"Wrote {len(m)} files to {OUT}")


if __name__ == "__main__":
    main()
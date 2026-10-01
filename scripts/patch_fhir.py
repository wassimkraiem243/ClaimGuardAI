"""Hardens fhir_parser.py and preflight.py. Safe to re-run: each edit is checked and skipped if already applied.
Run from the repo root:  python scripts/patch_fhir.py"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARSERS = ROOT / "apps" / "api" / "app" / "infrastructure" / "parsers"


def patch(path, edits):
    text = path.read_text(encoding="utf-8")  # universal newlines: CRLF files match too
    for label, old, new in edits:
        if new in text:
            print(f"  already applied  {label}")
        elif text.count(old) == 1:
            text = text.replace(old, new)
            print(f"  patched          {label}")
        else:
            print(f"  NOT FOUND ({text.count(old)} matches)  {label}  -> send me the file")
    path.write_text(text, encoding="utf-8", newline="\n")


print("fhir_parser.py")
patch(PARSERS / "fhir_parser.py", [
    ("imports", "import json\n", "import json\nimport math\n"),

    ("non-finite JSON constants", '_PROVIDER_TYPES = {"Practitioner", "Organization", "PractitionerRole"}\n',
     '_PROVIDER_TYPES = {"Practitioner", "Organization", "PractitionerRole"}\n\n\n'
     'class _NonFinite(Exception):\n    pass\n\n\n'
     'def _reject_constant(name):  # json.loads would otherwise accept NaN / Infinity\n'
     '    raise _NonFinite(f"Non-finite number in JSON: {name}")\n'),

    ("finite numbers only", "    return float(value)\n",
     "    f = float(value)\n    if not math.isfinite(f):  # 1e999 parses to inf\n"
     '        raise _rej("Number is not finite", path, cid)\n    return f\n'),

    ("safe json loading",
     '            bundle = json.loads(raw.decode("utf-8-sig"))\n'
     '        except (UnicodeDecodeError, json.JSONDecodeError):\n'
     '            raise IngestionRejected("Invalid JSON")\n',
     '            bundle = json.loads(raw.decode("utf-8-sig"), parse_constant=_reject_constant)\n'
     '        except _NonFinite as e:\n'
     '            raise IngestionRejected(str(e))\n'
     '        except RecursionError:\n'
     '            raise IngestionRejected("JSON is nested too deeply")\n'
     '        except (UnicodeDecodeError, json.JSONDecodeError):\n'
     '            raise IngestionRejected("Invalid JSON")\n'),

    ("claim use", "        w: list[str] = []\n        local = dict(index)\n",
     "        w: list[str] = []\n"
     '        if claim.get("use") not in (None, "claim"):\n'
     '            w.append(f"Claim.use={claim.get(\'use\')}: not a claim for payment")\n'
     "        local = dict(index)\n"),

    ("all item encounters",
     '        enc_ref = next((r for it in items if isinstance(it, dict)\n'
     '                        for r in (it.get("encounter") or []) if isinstance(r, dict)), None)\n'
     '        if enc_ref is None:\n'
     '            raise _rej("No claim item references an encounter", "Claim.item[].encounter", cid)\n'
     '        enc = res(enc_ref, {"Encounter"}, "Claim.item[].encounter[0]")\n',
     '        enc_refs = [r for it in items if isinstance(it, dict)\n'
     '                    for r in (it.get("encounter") or []) if isinstance(r, dict)]\n'
     '        if not enc_refs:\n'
     '            raise _rej("No claim item references an encounter", "Claim.item[].encounter", cid)\n'
     '        encs = [res(r, {"Encounter"}, "Claim.item[].encounter[0]") for r in enc_refs]\n'
     '        enc = encs[0]\n'
     '        if any(e is not enc for e in encs[1:]):\n'
     '            w.append("items reference several encounters; using the first")\n'),

    ("missing servicedDate warning",
     '            sdate = it.get("servicedDate") or (it.get("servicedPeriod") or {}).get("start")\n',
     '            sdate = it.get("servicedDate") or (it.get("servicedPeriod") or {}).get("start")\n'
     '            if sdate is None:\n'
     '                w.append(f"line {seq}: service_date missing")\n'),
])

print("preflight.py")
patch(PARSERS / "preflight.py", [
    ("deeply nested JSON",
     '    except json.JSONDecodeError as e:\n'
     '        raise InputRejected(f"Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}", "file")\n',
     '    except json.JSONDecodeError as e:\n'
     '        raise InputRejected(f"Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}", "file")\n'
     '    except RecursionError:\n'
     '        raise InputRejected("JSON is nested too deeply", "file")\n'),
])
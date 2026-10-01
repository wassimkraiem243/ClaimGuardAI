"""Last hardening pass: O(1) audit appends + claim_id on malformed FHIR errors.
Safe to re-run. Run from the repo root:  python scripts/patch_final.py"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "api" / "app" / "infrastructure"


def patch(path, edits):
    text = path.read_text(encoding="utf-8")
    for label, old, new in edits:
        if new in text:
            print(f"  already applied  {label}")
        elif text.count(old) == 1:
            text = text.replace(old, new)
            print(f"  patched          {label}")
        else:
            print(f"  NOT FOUND ({text.count(old)} matches)  {label}  -> send me the file")
    path.write_text(text, encoding="utf-8", newline="\n")


print("jsonl_audit.py")
patch(APP / "audit" / "jsonl_audit.py", [
    ("constant-time append: read only the last event",
     "    def append(self, type: str, claim_id: Optional[str], details: dict) -> AuditEvent:\n"
     "        with self._lock:\n"
     "            rows = self._rows()\n"
     '            prev = rows[-1]["hash"] if rows else GENESIS\n'
     '            payload = {"seq": len(rows) + 1,',
     "    def _last(self) -> tuple[int, str]:\n"
     '        """(seq, hash) of the last event, reading only the end of the file (O(1), not O(n))."""\n'
     "        if not self._path.exists():\n"
     "            return 0, GENESIS\n"
     '        with self._path.open("rb") as f:\n'
     "            f.seek(0, os.SEEK_END)\n"
     "            pos, data, step = f.tell(), b\"\", 4096\n"
     "            while pos > 0:\n"
     "                n = min(step, pos)\n"
     "                pos -= n\n"
     "                f.seek(pos)\n"
     "                data = f.read(n) + data\n"
     '                lines = data.rstrip(b"\\n").split(b"\\n")\n'
     "                if len(lines) > 1:  # the last line is complete once a newline precedes it\n"
     "                    break\n"
     "                step *= 2\n"
     '        data = data.rstrip(b"\\n")\n'
     "        if not data:\n"
     "            return 0, GENESIS\n"
     '        row = json.loads(data.split(b"\\n")[-1])\n'
     '        return row["seq"], row["hash"]\n'
     "\n"
     "    def append(self, type: str, claim_id: Optional[str], details: dict) -> AuditEvent:\n"
     "        with self._lock:\n"
     "            last_seq, prev = self._last()\n"
     '            payload = {"seq": last_seq + 1,'),
])

print("fhir_parser.py")
patch(APP / "parsers" / "fhir_parser.py", [
    ("claim_id on malformed-structure errors",
     "        try:\n"
     "            return [self._build(c, index) for c in claims]\n"
     "        except IngestionRejected:\n"
     "            raise\n"
     "        except (KeyError, TypeError, AttributeError, ValueError, IndexError) as e:\n"
     '            raise IngestionRejected(f"Malformed FHIR structure ({type(e).__name__})")\n',
     "        out = []\n"
     "        for c in claims:\n"
     "            try:\n"
     "                out.append(self._build(c, index))\n"
     "            except IngestionRejected:\n"
     "                raise\n"
     "            except (KeyError, TypeError, AttributeError, ValueError, IndexError) as e:\n"
     '                raise IngestionRejected(f"Malformed FHIR structure ({type(e).__name__})",\n'
     '                                        claim_id=None if c.get("id") is None else str(c["id"]))\n'
     "        return out\n"),
])
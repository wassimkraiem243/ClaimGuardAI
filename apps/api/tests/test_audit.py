import json
from app.infrastructure.audit.jsonl_audit import JsonlAuditLog


def make(tmp_path):
    log = JsonlAuditLog(tmp_path / "audit.jsonl")
    for i in range(4):
        log.append("CLAIM_INGESTED", f"C{i}", {"n": i})
    return log


def test_chain_is_valid_and_filterable(tmp_path):
    log = make(tmp_path)
    assert log.verify() == (True, None)
    assert [e.claim_id for e in log.read("C2")] == ["C2"] and len(log.read()) == 4


def test_tampering_is_detected(tmp_path):
    log = make(tmp_path)
    p = tmp_path / "audit.jsonl"
    rows = [json.loads(l) for l in p.read_text().splitlines()]
    rows[1]["details"]["n"] = 999
    p.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n")
    assert log.verify() == (False, 2)


def test_deletion_is_detected(tmp_path):
    log = make(tmp_path)
    p = tmp_path / "audit.jsonl"
    lines = p.read_text().splitlines()
    p.write_text("\n".join(lines[:1] + lines[2:]) + "\n")
    ok, bad = log.verify()
    assert not ok and bad == 2
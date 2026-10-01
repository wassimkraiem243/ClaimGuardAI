import time
from app.infrastructure.audit.jsonl_audit import JsonlAuditLog


def test_append_cost_does_not_grow_with_log_size(tmp_path):
    p = tmp_path / "a.jsonl"
    t = time.perf_counter()
    for i in range(1500):  # a fresh instance per call, like the router does
        JsonlAuditLog(p).append("FINDING_RAISED", f"C{i}", {"evidence": "x" * 200})
    assert time.perf_counter() - t < 5  # was ~4 s (quadratic) for 1500 events before the fix
    log = JsonlAuditLog(p)
    assert log.verify() == (True, None) and len(log.read()) == 1500


def test_last_event_larger_than_one_read_block(tmp_path):
    log = JsonlAuditLog(tmp_path / "a.jsonl")
    log.append("A", "C1", {"blob": "y" * 50_000})  # one line >> 4096 bytes
    e = log.append("B", "C2", {"n": 2})
    assert e.seq == 2 and log.verify() == (True, None)


def test_empty_and_new_file(tmp_path):
    log = JsonlAuditLog(tmp_path / "sub" / "a.jsonl")
    assert log._last() == (0, "0" * 64)
    assert log.append("A", None, {}).seq == 1
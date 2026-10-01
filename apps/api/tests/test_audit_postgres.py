import threading

import pytest
from sqlalchemy import text

from app.infrastructure.audit.postgres_audit import PostgresAuditLog, get_engine

TABLE = "audit_events_test"


@pytest.fixture()
def log():
    engine = get_engine()
    try:
        with engine.begin() as c:
            c.execute(text(f"DROP TABLE IF EXISTS {TABLE}"))
            c.execute(text(f"CREATE TABLE {TABLE} (LIKE audit_events INCLUDING ALL)"))
    except Exception as e:  # database not running: skip, don't fail the suite
        pytest.skip(f"PostgreSQL not available: {e.__class__.__name__}")
    yield PostgresAuditLog(engine, TABLE)
    with engine.begin() as c:
        c.execute(text(f"DROP TABLE IF EXISTS {TABLE}"))


def test_chain_valid_and_filterable(log):
    for i in range(4):
        log.append("CLAIM_INGESTED", f"C{i}", {"n": i, "amount": 120.5, "big": 1e15})
    assert log.verify() == (True, None)
    assert [e.claim_id for e in log.read("C2")] == ["C2"] and len(log.read()) == 4


def test_empty_log_verifies(log):
    assert log.verify() == (True, None)


def test_tampering_is_detected(log):
    for i in range(4):
        log.append("X", f"C{i}", {"n": i})
    with log._engine.begin() as c:
        c.execute(text(f"UPDATE {TABLE} SET details = '{{\"n\": 999}}'::jsonb WHERE seq = 2"))
    assert log.verify() == (False, 2)


def test_concurrent_writers_keep_chain_valid(log):
    errors: list[Exception] = []

    def work(w: int):
        try:
            for i in range(25):
                log.append("FINDING_RAISED", f"W{w}-{i}", {"w": w, "i": i})
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=work, args=(w,)) for w in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors
    assert log.verify() == (True, None)
    assert [e.seq for e in log.read()] == list(range(1, 201))
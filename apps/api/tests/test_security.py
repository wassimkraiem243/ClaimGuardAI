import time

import jwt
import pytest

from app import security as sec


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("CLAIMGUARD_JWT_SECRET", "x" * 40)


def test_password_round_trip_and_salting():
    h1, h2 = sec.hash_password("s3cret!"), sec.hash_password("s3cret!")
    assert h1 != h2  # per-password random salt
    assert sec.verify_password("s3cret!", h1) and not sec.verify_password("wrong", h1)
    assert not sec.verify_password("s3cret!", "garbage") and not sec.verify_password("x", "md5$a$b")


def test_token_round_trip():
    c = sec.decode_token(sec.create_token("nour", "analyst"))
    assert c["sub"] == "nour" and c["role"] == "analyst"


def test_expired_token_is_rejected():
    with pytest.raises(sec.AuthError):
        sec.decode_token(sec.create_token("nour", "analyst", ttl_seconds=-5))


def test_tampered_token_is_rejected():
    t = sec.create_token("nour", "analyst")
    head, body, sig = t.split(".")
    forged = jwt.encode({"sub": "nour", "role": "admin", "exp": int(time.time()) + 999}, "y" * 40, algorithm="HS256")
    for bad in (f"{head}.{body}.{sig[:-2]}AA", forged):
        with pytest.raises(sec.AuthError):
            sec.decode_token(bad)


def test_alg_none_is_rejected():
    unsigned = jwt.encode({"sub": "x", "role": "admin", "exp": int(time.time()) + 999}, key=None, algorithm="none")
    with pytest.raises(sec.AuthError):
        sec.decode_token(unsigned)


def test_unknown_role_and_missing_secret(monkeypatch):
    with pytest.raises(ValueError):
        sec.create_token("x", "root")
    monkeypatch.delenv("CLAIMGUARD_JWT_SECRET")
    with pytest.raises(RuntimeError):
        sec.create_token("x", "analyst")


def test_role_check():
    assert sec.has_role({"role": "auditor"}, ("auditor",))
    assert not sec.has_role({"role": "analyst"}, ("auditor",))
    assert sec.has_role({"role": "admin"}, ("auditor",))
"""Authentication primitives: password hashing (scrypt) and signed, expiring JWTs with a role claim.
No FastAPI here: pure functions, easy to test. Wiring comes in the router layer."""
import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

import jwt

ALGORITHM = "HS256"
ROLES = ("analyst", "auditor", "admin")
_SCRYPT = dict(n=2**14, r=8, p=1, dklen=32)


def _secret() -> str:
    s = os.environ.get("CLAIMGUARD_JWT_SECRET")
    if not s or len(s) < 32:
        raise RuntimeError("CLAIMGUARD_JWT_SECRET must be set (at least 32 characters)")
    return s


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, dk_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(dk_b64)
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)
    return hmac.compare_digest(actual, expected)  # constant-time comparison


def create_token(subject: str, role: str, ttl_seconds: int = 3600) -> str:
    if role not in ROLES:
        raise ValueError(f"unknown role: {role!r}")
    now = int(time.time())
    return jwt.encode({"sub": subject, "role": role, "iat": now, "exp": now + ttl_seconds},
                      _secret(), algorithm=ALGORITHM)


class AuthError(Exception):
    pass


def decode_token(token: str) -> dict:
    """Verify signature and expiry. The algorithm is pinned: 'alg: none' and key-confusion tokens fail."""
    try:
        claims = jwt.decode(token, _secret(), algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError as e:
        raise AuthError(str(e)) from e
    if claims.get("role") not in ROLES:
        raise AuthError("invalid role claim")
    return claims


def has_role(claims: dict, allowed: tuple[str, ...]) -> bool:
    return claims.get("role") in allowed or claims.get("role") == "admin"
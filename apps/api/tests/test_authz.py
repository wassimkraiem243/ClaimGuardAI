# tests/conftest.py
import os
import time

# Must run BEFORE the app is imported, so config picks up the test secret.
os.environ.setdefault("CLAIMGUARD_JWT_SECRET", "test-secret-" + "x" * 40)  # 32+ bytes

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app


def _make_token(sub: str, role: str, expires_in: int = 3600) -> str:
    now = int(time.time())
    payload = {"sub": sub, "role": role, "iat": now, "exp": now + expires_in}
    return jwt.encode(payload, os.environ["CLAIMGUARD_JWT_SECRET"], algorithm="HS256")


def _headers(role: str) -> dict:
    return {"Authorization": f"Bearer {_make_token(f'test-{role}', role)}"}


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def admin_headers():
    return _headers("admin")


@pytest.fixture
def analyst_headers():
    return _headers("analyst")


@pytest.fixture
def auditor_headers():
    return _headers("auditor")
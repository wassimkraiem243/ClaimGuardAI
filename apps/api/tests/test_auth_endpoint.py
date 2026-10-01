import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import security
from app.infrastructure.audit.postgres_audit import get_engine
from app.infrastructure.repositories.postgres_users import PostgresUserRepository
from app.routers import auth


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("CLAIMGUARD_JWT_SECRET", "x" * 40)
    engine = get_engine()
    try:
        with engine.begin() as c:
            c.execute(text("DELETE FROM users WHERE username LIKE 'test-%'"))
    except Exception as e:
        pytest.skip(f"PostgreSQL not available (or migration 0003 not applied): {e.__class__.__name__}")
    repo = PostgresUserRepository(engine)
    repo.create("test-ana", security.hash_password("correct-horse-battery"), "analyst")
    repo.create("test-off", security.hash_password("correct-horse-battery"), "auditor")
    with engine.begin() as c:
        c.execute(text("UPDATE users SET disabled = true WHERE username = 'test-off'"))
    monkeypatch.setattr(auth, "get_user_repository", lambda: repo)
    app = FastAPI()
    app.include_router(auth.router)
    yield TestClient(app)
    with engine.begin() as c:
        c.execute(text("DELETE FROM users WHERE username LIKE 'test-%'"))


def login(c, user, pw):
    return c.post("/auth/token", data={"username": user, "password": pw})


def test_login_returns_a_token_with_the_right_role(client):
    r = login(client, "test-ana", "correct-horse-battery")
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
    claims = security.decode_token(r.json()["access_token"])
    assert claims["sub"] == "test-ana" and claims["role"] == "analyst"


def test_failures_are_indistinguishable(client):
    bad = [login(client, "test-ana", "wrong-password-xx"),
           login(client, "test-nobody", "correct-horse-battery"),
           login(client, "test-off", "correct-horse-battery")]  # disabled account
    assert all(r.status_code == 401 for r in bad)
    assert len({r.json()["detail"] for r in bad}) == 1
    assert all(r.headers["www-authenticate"] == "Bearer" for r in bad)
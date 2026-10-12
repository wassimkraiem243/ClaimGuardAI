from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_cors_rejects_unknown_origin():
    r = client.options("/health", headers={"Origin": "https://evil.example",
                                           "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_cors_allows_configured_origin():
    origin = settings.cors_origin_list()[0]
    r = client.options("/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == origin


def test_empty_and_wrong_api_key_are_rejected():
    assert client.get("/v1/rules").status_code == 401
    assert client.get("/v1/rules", headers={"x-api-key": ""}).status_code == 401
    assert client.get("/v1/rules", headers={"x-api-key": "wrong"}).status_code == 401
    assert client.get("/v1/rules", headers={"x-api-key": settings.api_key}).status_code == 200

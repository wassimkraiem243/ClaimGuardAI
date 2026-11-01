import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"x-api-key": "dev-local-key"}


@pytest.fixture()
def client():
    return TestClient(app)


def test_benchmark_validation_split(client):
    r = client.get("/v1/benchmark/splits/validation", headers=HEADERS)
    if r.status_code == 404:
        pytest.skip("metrics.json missing")
    assert r.status_code == 200
    body = r.json()
    assert body["split"] == "validation"
    assert body["n_claims"] == 50


def test_security_overview(client):
    r = client.get("/v1/security/overview", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "markdown" in body
    assert body["controls"]["fhir_preflight"] is True

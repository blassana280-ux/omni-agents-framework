"""API FastAPI : endpoints, tableau de bord, authentification par token."""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from cf100.api.app import create_app  # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("CF100_API_TOKEN", raising=False)
    return TestClient(create_app())


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["divisions"] == 10
    assert body["agents"] == 100


def test_divisions_and_agents(client):
    divisions = client.get("/divisions").json()
    assert len(divisions) == 10
    agents = client.get("/agents").json()
    assert len(agents) == 100
    detail = client.get("/agents/CI-001")
    assert detail.status_code == 200
    assert client.get("/agents/XX-999").status_code == 404


def test_evaluation_endpoint_honest(client):
    report = client.get("/evaluation").json()
    assert report["summary"]["total"] == 100
    # sans agents en exécution : inactifs, jamais « opérationnels »
    assert report["summary"]["inactif"] == 100
    assert report["summary"]["opérationnel"] == 0


def test_evidence_and_dashboard(client):
    verdict = client.get("/evidence/verify").json()
    assert verdict["ok"] is True
    html = client.get("/dashboard")
    assert html.status_code == 200
    assert "Cyber Force 100" in html.text
    assert "<script src" not in html.text  # aucun CDN, aucune ressource externe


def test_token_auth(monkeypatch):
    monkeypatch.setenv("CF100_API_TOKEN", "jeton-de-test")
    app = create_app()
    client = TestClient(app)
    # sans token : refus (sauf routes ouvertes)
    assert client.get("/agents").status_code == 401
    assert client.get("/divisions").status_code == 401
    assert client.get("/health").status_code == 200       # ouverte
    assert client.get("/dashboard").status_code == 200   # ouverte
    # mauvais token : refus
    r = client.get("/agents", headers={"X-API-Token": "mauvais"})
    assert r.status_code == 401
    # bon token : accès
    r = client.get("/agents", headers={"X-API-Token": "jeton-de-test"})
    assert r.status_code == 200
    assert len(r.json()) == 100

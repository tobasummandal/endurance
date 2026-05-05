import pytest
from fastapi.testclient import TestClient
from helios.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_create_session_and_get(client):
    src = "def add(a, b):\n    return a + b\n"
    r = client.post("/api/sessions", json={"filename": "x.py", "source_code": src})
    assert r.status_code == 200, r.text
    sid = r.json()["id"]

    r2 = client.get(f"/api/sessions/{sid}")
    assert r2.status_code == 200
    assert r2.json()["filename"] == "x.py"


def test_create_session_rejects_empty(client):
    r = client.post("/api/sessions", json={"filename": "x.py", "source_code": "   "})
    assert r.status_code == 400

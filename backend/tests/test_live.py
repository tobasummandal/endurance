import pytest
from fastapi.testclient import TestClient

from helios.live.cache import cache
from helios.live.ratelimit import limiter
from helios.live.stats import stats
from helios.main import app


@pytest.fixture(autouse=True)
def _reset():
    cache.reset()
    limiter.reset()
    # snapshot stats for delta-style assertions
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ---- Phase 1 ----

def test_live_static_returns_findings(client):
    src = "def f(x=[]):\n    pass\n"
    r = client.post("/api/live/audit/static", json={"filename": "x.py", "source_code": src})
    assert r.status_code == 200, r.text
    body = r.json()
    cats = [f["category"] for f in body["findings"]]
    assert "mutable_default" in cats
    assert body["elapsed_ms"] >= 0


def test_live_static_rejects_oversize(client, monkeypatch):
    from helios import config
    monkeypatch.setattr(config.settings, "live_max_file_lines", 5)
    big = "\n".join(f"x{i} = {i}" for i in range(20))
    r = client.post("/api/live/audit/static", json={"filename": "x.py", "source_code": big})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "file_too_large_for_live"


def test_live_static_rate_limited(client, monkeypatch):
    from helios import config
    from helios.live.ratelimit import RateLimiter
    import helios.api.live as live_module
    tiny = RateLimiter(capacity=1, refill_per_s=0.0)
    monkeypatch.setattr(live_module, "limiter", tiny)
    src = "x = 1\n"
    headers = {"x-session-token": "t1"}
    r1 = client.post("/api/live/audit/static",
                     json={"filename": "x.py", "source_code": src},
                     headers=headers)
    assert r1.status_code == 200
    r2 = client.post("/api/live/audit/static",
                     json={"filename": "x.py", "source_code": src},
                     headers=headers)
    assert r2.status_code == 429
    assert r2.json()["error"]["code"] == "rate_limited"


# ---- Phase 2 (no LLM key — just verify SSE shape & static event) ----

def test_live_stream_emits_static_event(client, monkeypatch):
    # short-circuit LLM so the test doesn't hit Gemini
    import helios.api.live as live_module
    def fake_audit(*a, **kw):
        return []
    monkeypatch.setattr(live_module, "run_llm_audit", fake_audit)

    src = "def f():\n    for i in range(1, 10):\n        pass\n"
    headers = {"x-session-token": "stream-t1"}
    with client.stream("POST", "/api/live/audit/stream",
                       json={"filename": "x.py", "source_code": src},
                       headers=headers) as r:
        assert r.status_code == 200
        body = b"".join(r.iter_bytes()).decode()
    # Must contain the SSE frames
    assert "event: static" in body
    assert "event: done" in body
    # off_by_one is detected by static rules
    assert "off_by_one" in body


def test_live_stream_full_cache_skips_llm(client, monkeypatch):
    import helios.api.live as live_module
    calls = {"n": 0}
    def fake_audit(*a, **kw):
        calls["n"] += 1
        return []
    monkeypatch.setattr(live_module, "run_llm_audit", fake_audit)

    src = "def f():\n    return 1\n"
    headers = {"x-session-token": "stream-cache"}
    payload = {"filename": "x.py", "source_code": src}

    with client.stream("POST", "/api/live/audit/stream", json=payload, headers=headers) as r:
        b1 = b"".join(r.iter_bytes()).decode()
    first_calls = calls["n"]

    with client.stream("POST", "/api/live/audit/stream", json=payload, headers=headers) as r:
        b2 = b"".join(r.iter_bytes()).decode()

    assert "event: cache_hit" in b2
    assert calls["n"] == first_calls  # no new LLM calls on cache hit


# ---- Phase 3 ----

def test_fix_preview_calls_generator(client, monkeypatch):
    import helios.api.live as live_module
    def fake_fix(filename, src, issue):
        return {"fixed_code": "fixed", "diff_summary": "did stuff"}
    monkeypatch.setattr(live_module, "generate_fix", fake_fix)

    finding = {
        "category": "off_by_one", "severity": "high",
        "line_start": 1, "line_end": 1,
        "title": "off by one", "explanation": "loop starts at 1",
        "source": "static",
    }
    r = client.post("/api/live/fix/preview", json={
        "filename": "x.py",
        "source_code": "def f():\n    pass\n",
        "finding": finding,
    })
    assert r.status_code == 200, r.text
    assert r.json() == {"fixed_code": "fixed", "diff_summary": "did stuff"}


# ---- Phase 4 ----

def test_stats_endpoint(client):
    r0 = client.get("/api/live/stats")
    assert r0.status_code == 200
    base = r0.json()
    client.post("/api/live/audit/static",
                json={"filename": "x.py", "source_code": "x = 1\n"})
    r1 = client.get("/api/live/stats")
    assert r1.json()["static_calls"] >= base["static_calls"] + 1

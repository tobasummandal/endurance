"""Pattern A — agent client + review() + tool schemas."""
from __future__ import annotations
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient

from helios.agent.client import HeliosClient
from helios.agent.review import review_code
from helios.agent.tool_schema import ANTHROPIC_TOOLS, OPENAI_TOOLS, TOOL_SCHEMAS
from helios.live.cache import cache
from helios.live.ratelimit import limiter
from helios.main import app


@pytest.fixture(autouse=True)
def _reset():
    cache.reset()
    limiter.reset()
    yield


@pytest.fixture(scope="module")
def live_server():
    """Run the real Helios FastAPI app on a free port for HTTP-level tests."""
    cfg = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning")
    server = uvicorn.Server(cfg)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    # wait for boot
    for _ in range(40):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started, "test server failed to start"
    yield "http://127.0.0.1:8765"
    server.should_exit = True
    thread.join(timeout=2)


def test_review_static_only_on_scientific(live_server, monkeypatch):
    cache.reset(); limiter.reset()
    src = """
import numpy as np

def integrate(f, dx):
    n = len(f)
    total = 0.0
    for i in range(1, n - 1):
        total += 0.5 * (f[i] + f[i + 1]) * dx
    return total
"""
    cl = HeliosClient(base_url=live_server)
    rev = review_code(src, deep=False, client=cl)
    assert rev.is_scientific
    assert rev.warning is None
    assert any(f["category"] == "off_by_one" for f in rev.findings)


def test_review_warns_on_non_scientific(live_server):
    cache.reset(); limiter.reset()
    src = """
from fastapi import APIRouter
router = APIRouter()

@router.get("/x")
def f():
    try:
        return 1
    except:
        return 0
"""
    cl = HeliosClient(base_url=live_server)
    rev = review_code(src, deep=False, client=cl)
    assert rev.is_scientific is False
    assert rev.warning is not None
    assert "scientific" in rev.warning.lower()


def test_to_agent_text_renders(live_server):
    cache.reset(); limiter.reset()
    src = "def f(x=[]):\n    pass\n"
    cl = HeliosClient(base_url=live_server)
    rev = review_code(src, deep=False, client=cl)
    text = rev.to_agent_text()
    assert "mutable_default" in text or "Findings" in text or rev.error


def test_tool_schema_shape():
    # Anthropic-style
    names = {t["name"] for t in ANTHROPIC_TOOLS}
    assert "helios_audit" in names
    assert "helios_fix_preview" in names
    for t in ANTHROPIC_TOOLS:
        assert "input_schema" in t
        assert t["input_schema"]["type"] == "object"

    # OpenAI-style
    for t in OPENAI_TOOLS:
        assert t["type"] == "function"
        assert "parameters" in t["function"]

    assert "openai" in TOOL_SCHEMAS and "anthropic" in TOOL_SCHEMAS


def test_descriptions_emphasize_scientific_scope():
    """The whole point of the schemas: agents self-gate non-scientific calls."""
    for t in ANTHROPIC_TOOLS:
        if "audit" in t["name"] or "route" in t["name"]:
            d = t["description"].lower()
            assert "scientific" in d or "numerical" in d

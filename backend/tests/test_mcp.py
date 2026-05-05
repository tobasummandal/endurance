"""Pattern C — MCP server tool definitions & dispatch shape.

We don't spin up the actual stdio transport; instead we exercise the tool
list and the in-process dispatcher. Backend HTTP calls are mocked.
"""
from __future__ import annotations
import json

import pytest

mcp = pytest.importorskip("mcp", reason="mcp SDK not installed")

from helios.mcp_server import server as mcp_server  # noqa: E402


def _text(content_list) -> str:
    return content_list[0].text


def test_tool_list_includes_required_tools():
    names = {t.name for t in mcp_server.TOOLS}
    for required in [
        "helios_audit",
        "helios_fix_preview",
        "helios_session_create",
        "helios_session_audit",
        "helios_session_fix",
        "helios_session_verify",
        "helios_session_route",
        "helios_detect_scientific",
    ]:
        assert required in names, f"missing tool: {required}"


def test_tool_descriptions_emphasize_scientific():
    for t in mcp_server.TOOLS:
        if t.name in ("helios_audit", "helios_session_audit", "helios_session_route"):
            d = t.description.lower()
            assert "scientific" in d or "numerical" in d


@pytest.mark.asyncio
async def test_detect_scientific_tool():
    src = "import numpy as np\nx = np.zeros(10)\n"
    out = await mcp_server._call("helios_detect_scientific", {"source_code": src})
    payload = json.loads(_text(out))
    assert payload["is_scientific"] is True


@pytest.mark.asyncio
async def test_audit_attaches_warning_on_non_scientific(monkeypatch):
    # stub the HTTP audit so we don't need a running server
    class FakeReview:
        def __init__(self):
            self.is_scientific = False
            self.warning = "warned"
            self.findings = []
            self.summary = "ok"
        def to_dict(self):
            return {
                "is_scientific": False,
                "warning": "warned",
                "findings": [],
                "summary": "ok",
                "detector": {"score": 0.0, "is_scientific": False,
                             "confidence": "high", "reason": "web",
                             "positive_signals": [], "negative_signals": ["web_decorator"]},
            }
    monkeypatch.setattr(mcp_server, "review_code",
                        lambda src, **kw: FakeReview())
    src = "@app.route('/x')\ndef f(): pass\n"
    out = await mcp_server._call("helios_audit", {"source_code": src})
    payload = json.loads(_text(out))
    assert payload["warning"] == "warned"
    assert payload["is_scientific"] is False


@pytest.mark.asyncio
async def test_unknown_tool_errors():
    out = await mcp_server._call("does_not_exist", {})
    payload = json.loads(_text(out))
    assert "error" in payload

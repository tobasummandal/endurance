"""Typed HTTP client for the Helios backend.

The agent integration uses this rather than calling Helios's internal
modules directly — keeps the seam clean and lets the agent run in a
different process / machine from the analysis backend.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_BASE_URL = os.environ.get("HELIOS_API_URL", "http://localhost:8000")
DEFAULT_TIMEOUT_S = float(os.environ.get("HELIOS_TIMEOUT_S", "120"))


class HeliosClientError(RuntimeError):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        super().__init__(f"[{status} {code}] {message}")
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass
class HeliosClient:
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = DEFAULT_TIMEOUT_S
    session_token: str | None = None

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.session_token:
            h["X-Session-Token"] = self.session_token
        return h

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url.rstrip('/')}{path}"
        with httpx.Client(timeout=self.timeout_s) as c:
            r = c.request(method, url, headers=self._headers(), **kwargs)
        if r.status_code >= 400:
            try:
                err = r.json().get("error", {})
                raise HeliosClientError(
                    r.status_code,
                    err.get("code", "unknown"),
                    err.get("message", r.text[:200]),
                    err.get("details"),
                )
            except (ValueError, KeyError):
                raise HeliosClientError(r.status_code, "unknown", r.text[:200])
        return r.json()

    # ---- live (stateless) ----
    def audit_static(self, source: str, filename: str = "draft.py") -> dict:
        return self._request(
            "POST", "/live/audit/static",
            json={"filename": filename, "source_code": source,
                  "session_token": self.session_token},
        )

    def audit(self, source: str, filename: str = "draft.py") -> dict:
        """Buffered audit: runs static + LLM, returns merged findings.

        Uses the streaming endpoint server-side but consolidates the response
        into a single dict for callers that don't need progressive results.
        """
        url = f"{self.base_url.rstrip('/')}/live/audit/stream"
        merged: list[dict] = []
        static: list[dict] = []
        llm: list[dict] = []
        with httpx.Client(timeout=self.timeout_s) as c:
            with c.stream(
                "POST", url, headers=self._headers(),
                json={"filename": filename, "source_code": source,
                      "session_token": self.session_token},
            ) as r:
                if r.status_code >= 400:
                    raise HeliosClientError(r.status_code, "stream_failed", r.read().decode()[:200])
                event = ""
                buf: list[str] = []
                for raw in r.iter_lines():
                    if not raw:
                        if event and buf:
                            data = "\n".join(buf)
                            try:
                                payload = __import__("json").loads(data)
                            except Exception:
                                payload = None
                            if event == "static" and isinstance(payload, list):
                                static = payload
                            elif event == "llm" and isinstance(payload, list):
                                llm = payload
                            elif event == "merged" and isinstance(payload, list):
                                merged = payload
                        event, buf = "", []
                        continue
                    if raw.startswith("event:"):
                        event = raw.split(":", 1)[1].strip()
                    elif raw.startswith("data:"):
                        buf.append(raw.split(":", 1)[1].strip())
        return {"findings": merged or static, "static": static, "llm": llm}

    def fix_preview(self, source: str, finding: dict, filename: str = "draft.py") -> dict:
        return self._request(
            "POST", "/live/fix/preview",
            json={"filename": filename, "source_code": source, "finding": finding},
        )

    # ---- persisted (full session lifecycle) ----
    def create_session(self, source: str, filename: str = "draft.py") -> dict:
        return self._request("POST", "/sessions",
                             json={"filename": filename, "source_code": source})

    def session_audit(self, session_id: str) -> list[dict]:
        return self._request("POST", f"/sessions/{session_id}/audit")

    def session_fix(self, session_id: str, issue_id: str) -> dict:
        return self._request("POST", f"/sessions/{session_id}/issues/{issue_id}/fix")

    def session_verify(self, session_id: str, fix_id: str) -> dict:
        return self._request("POST", f"/sessions/{session_id}/fixes/{fix_id}/verify")

    def session_route(self, session_id: str) -> dict:
        return self._request("POST", f"/sessions/{session_id}/route")

    # ---- meta ----
    def health(self) -> dict:
        return self._request("GET", "/health")

    def stats(self) -> dict:
        return self._request("GET", "/live/stats")

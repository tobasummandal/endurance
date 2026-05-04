"""Per-session, per-function AST-hash cache for live LLM audit.

Key idea: re-auditing identical code is a waste. We hash each function's AST
and cache the LLM findings keyed by (session_token, function_name, ast_hash).
If the user edits one function, we only re-audit that function.
"""
from __future__ import annotations
import ast
import hashlib
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Iterable

from ..config import settings


def function_hash(fn: ast.FunctionDef) -> str:
    return hashlib.sha256(ast.dump(fn).encode()).hexdigest()[:16]


def file_hash(source: str) -> str:
    return hashlib.sha256(source.encode()).hexdigest()[:16]


@dataclass
class _SessionEntry:
    # function_name -> (ast_hash, list[finding_dict])
    functions: Dict[str, tuple[str, list[dict]]] = field(default_factory=dict)
    last_full_hash: str = ""
    last_full_findings: list[dict] = field(default_factory=list)
    last_used: float = field(default_factory=time.monotonic)


class LiveCache:
    def __init__(self, max_tokens: int, ttl_s: int) -> None:
        self.max_tokens = max_tokens
        self.ttl_s = ttl_s
        self._sessions: Dict[str, _SessionEntry] = {}
        self._lock = Lock()

    def _gc_locked(self) -> None:
        now = time.monotonic()
        # ttl eviction
        stale = [k for k, v in self._sessions.items() if now - v.last_used > self.ttl_s]
        for k in stale:
            self._sessions.pop(k, None)
        # capacity eviction (LRU-ish: oldest last_used)
        if len(self._sessions) > self.max_tokens:
            ordered = sorted(self._sessions.items(), key=lambda kv: kv[1].last_used)
            for k, _ in ordered[: len(self._sessions) - self.max_tokens]:
                self._sessions.pop(k, None)

    def lookup_full(self, token: str, source: str) -> list[dict] | None:
        """Whole-file hash match — return cached findings if source unchanged."""
        h = file_hash(source)
        with self._lock:
            self._gc_locked()
            entry = self._sessions.get(token)
            if entry and entry.last_full_hash == h:
                entry.last_used = time.monotonic()
                return list(entry.last_full_findings)
            return None

    def store_full(self, token: str, source: str, findings: list[dict]) -> None:
        h = file_hash(source)
        with self._lock:
            entry = self._sessions.setdefault(token, _SessionEntry())
            entry.last_full_hash = h
            entry.last_full_findings = list(findings)
            entry.last_used = time.monotonic()
            self._gc_locked()

    def split_by_function(
        self, token: str, source: str
    ) -> tuple[list[dict], list[ast.FunctionDef]]:
        """Return (cached_findings_for_unchanged_fns, list_of_functions_needing_audit)."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return [], []
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        cached_findings: list[dict] = []
        need_audit: list[ast.FunctionDef] = []
        with self._lock:
            self._gc_locked()
            entry = self._sessions.setdefault(token, _SessionEntry())
            entry.last_used = time.monotonic()
            seen_now: set[str] = set()
            for fn in functions:
                seen_now.add(fn.name)
                h = function_hash(fn)
                cached = entry.functions.get(fn.name)
                if cached and cached[0] == h:
                    cached_findings.extend(cached[1])
                else:
                    need_audit.append(fn)
            # drop entries for functions deleted in current source
            for stale in [k for k in entry.functions if k not in seen_now]:
                entry.functions.pop(stale, None)
        return cached_findings, need_audit

    def store_function_findings(
        self, token: str, fn: ast.FunctionDef, findings: list[dict]
    ) -> None:
        with self._lock:
            entry = self._sessions.setdefault(token, _SessionEntry())
            entry.functions[fn.name] = (function_hash(fn), list(findings))
            entry.last_used = time.monotonic()

    def active_tokens(self) -> int:
        with self._lock:
            self._gc_locked()
            return len(self._sessions)

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()


cache = LiveCache(
    max_tokens=settings.live_cache_max_tokens,
    ttl_s=settings.live_cache_ttl_s,
)

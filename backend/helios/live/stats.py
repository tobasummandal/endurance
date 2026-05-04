"""In-memory telemetry counters. Exposed via /live/stats."""
from __future__ import annotations
from threading import Lock
from typing import Dict


class Stats:
    def __init__(self) -> None:
        self._counts: Dict[str, int] = {
            "static_calls": 0,
            "stream_calls": 0,
            "fix_preview_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cancellations": 0,
            "rate_limited": 0,
        }
        self._lock = Lock()

    def inc(self, key: str, n: int = 1) -> None:
        with self._lock:
            self._counts[key] = self._counts.get(key, 0) + n

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counts)


stats = Stats()

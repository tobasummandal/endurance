"""Per-token token-bucket rate limiter. Lives in memory; one process only."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict

from ..config import settings


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    def __init__(self, capacity: int, refill_per_s: float) -> None:
        self.capacity = capacity
        self.refill = refill_per_s
        self._buckets: Dict[str, _Bucket] = {}
        self._lock = Lock()

    def take(self, key: str, cost: float = 1.0) -> bool:
        now = time.monotonic()
        with self._lock:
            b = self._buckets.get(key)
            if b is None:
                b = _Bucket(tokens=float(self.capacity), last_refill=now)
                self._buckets[key] = b
            elapsed = now - b.last_refill
            b.tokens = min(self.capacity, b.tokens + elapsed * self.refill)
            b.last_refill = now
            if b.tokens >= cost:
                b.tokens -= cost
                return True
            return False

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


limiter = RateLimiter(
    capacity=settings.live_rate_capacity,
    refill_per_s=settings.live_rate_refill_per_s,
)

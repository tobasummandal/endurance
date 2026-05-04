"""Track in-flight LLM tasks per session token; cancel previous on new request."""
from __future__ import annotations
import asyncio
from threading import Lock
from typing import Dict


class InFlight:
    def __init__(self) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = Lock()

    def claim(self, token: str, task: asyncio.Task) -> asyncio.Task | None:
        """Register `task` as the current job for `token`. Return prior task (caller cancels)."""
        with self._lock:
            prior = self._tasks.get(token)
            self._tasks[token] = task
            return prior

    def release(self, token: str, task: asyncio.Task) -> None:
        with self._lock:
            cur = self._tasks.get(token)
            if cur is task:
                self._tasks.pop(token, None)

    def reset(self) -> None:
        with self._lock:
            self._tasks.clear()


inflight = InFlight()

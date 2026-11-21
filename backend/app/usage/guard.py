"""Small in-process controls to reduce unnecessary Onshape requests.

These counters describe requests made through this running application only;
they are not a replacement for the authoritative usage display in Onshape.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any


class RequestGuard:
    def __init__(self, max_concurrent: int = 2, cache_ttl: int = 30) -> None:
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, Any]] = {}
        self._successful_calls = 0
        self._by_status: dict[str, int] = defaultdict(int)

    def cache_get(self, key: str) -> Any | None:
        item = self._cache.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at <= time.monotonic():
            self._cache.pop(key, None)
            return None
        return value

    def cache_set(self, key: str, value: Any) -> None:
        self._cache[key] = (time.monotonic() + self.cache_ttl, value)

    def record(self, status_code: int) -> None:
        self._by_status[str(status_code)] += 1
        if 200 <= status_code < 400:
            self._successful_calls += 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "successful_calls_recorded_by_app": self._successful_calls,
            "responses_by_status": dict(self._by_status),
            "note": "App-local counters only; check Onshape Developer settings for the authoritative account allocation.",
        }

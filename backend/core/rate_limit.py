"""Replace RateLimiter with a shared Redis adapter for multi-instance deployments."""

import time
from collections import deque
from typing import Protocol

from fastapi import HTTPException


class RateLimiter(Protocol):
    def check(self, key: str, limit: int, window: float) -> None: ...
    def failure(self, key: str) -> None: ...
    def success(self, key: str) -> None: ...


class MemoryRateLimiter:
    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = {}
        self.failures: dict[str, tuple[int, float]] = {}

    def check(self, key: str, limit: int = 10, window: float = 60) -> None:
        now = time.monotonic()
        failures, until = self.failures.get(key, (0, 0))
        if until > now:
            raise HTTPException(
                429,
                "Too many attempts. Wait before retrying.",
                headers={"Retry-After": str(max(1, int(until - now)))},
            )
        # Bound memory for clients which repeatedly vary their identity.
        if len(self.hits) > 10000:
            self.hits = {k: v for k, v in self.hits.items() if v and v[-1] > now - 900}
        queue = self.hits.setdefault(key, deque())
        while queue and queue[0] <= now - window:
            queue.popleft()
        if len(queue) >= limit:
            raise HTTPException(
                429,
                "Too many attempts. Wait before retrying.",
                headers={"Retry-After": str(int(window))},
            )
        queue.append(now)

    def failure(self, key: str) -> None:
        count, until = self.failures.get(key, (0, 0))
        if until < time.monotonic() - 900:
            count = 0
        count += 1
        if len(self.failures) >= 10000 and key not in self.failures:
            self.failures.pop(next(iter(self.failures)))
        self.failures[key] = (
            count,
            time.monotonic() + (min(900, 2 ** min(count, 10)) if count >= 5 else 0),
        )

    def success(self, key: str) -> None:
        self.failures.pop(key, None)


limiter: RateLimiter = MemoryRateLimiter()

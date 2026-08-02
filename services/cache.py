"""A minimal thread-safe TTL cache for fetched ConfiForms data.

Avoids hitting Confluence on every dashboard request/poll; entries expire
after `ttl_seconds` and are recomputed lazily on next access.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._value: T | None = None
        self._fetched_at: float = 0.0

    def get_or_fetch(self, fetch_fn: Callable[[], T]) -> T:
        """Return the cached value if fresh, otherwise call fetch_fn and cache it."""
        with self._lock:
            now = time.monotonic()
            is_fresh = self._value is not None and (now - self._fetched_at) < self.ttl_seconds
            if is_fresh:
                return self._value  # type: ignore[return-value]

            value = fetch_fn()
            self._value = value
            self._fetched_at = now
            return value

    def invalidate(self) -> None:
        with self._lock:
            self._value = None
            self._fetched_at = 0.0

    @property
    def age_seconds(self) -> float:
        with self._lock:
            if self._value is None:
                return float("inf")
            return time.monotonic() - self._fetched_at

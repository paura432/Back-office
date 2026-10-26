"""Small thread-safe in-process TTL cache for local inventory reads."""

from copy import deepcopy
from math import ulp
from threading import RLock
from time import monotonic
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Cache values by key until their monotonic expiration time."""

    def __init__(self, ttl_seconds: float, clock: Callable[[], float] = monotonic):
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[object, tuple[float, T]] = {}
        self._lock = RLock()

    def get_or_set(self, key: object, factory: Callable[[], T]) -> T:
        """Return a live entry or calculate and store a fresh value."""
        with self._lock:
            now = self._clock()
            entry = self._entries.get(key)
            if entry is not None and not self._expired(entry[0], now):
                return deepcopy(entry[1])

            value = factory()
            self._entries[key] = (now + self.ttl_seconds, deepcopy(value))
            return deepcopy(value)

    def _expired(self, expires_at: float, now: float) -> bool:
        """Treat values at the TTL boundary as expired despite float rounding."""
        return now >= expires_at or expires_at - now <= max(ulp(expires_at), ulp(now))

    def invalidate(self, key: object | None = None) -> None:
        """Invalidate one entry, or every entry when key is omitted."""
        with self._lock:
            if key is None:
                self._entries.clear()
            else:
                self._entries.pop(key, None)

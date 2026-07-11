"""Bounded in-memory LRU cache with TTL support."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from typing import Any, Generic, TypeVar

V = TypeVar("V")


class CacheEntry(Generic[V]):
    """A single cache entry with an expiry timestamp."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: V, ttl: float) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl

    @property
    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at


class TTLCache(Generic[V]):
    """Thread-safe (asyncio-safe) LRU cache with TTL expiry.

    Uses an asyncio Lock for concurrent safety in an async environment.
    Cache is bounded by ``maxsize``; when full, the least-recently-used
    entry is evicted.
    """

    def __init__(self, maxsize: int = 512, default_ttl: float = 300.0) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self._maxsize = maxsize
        self._default_ttl = default_ttl
        self._store: OrderedDict[str, CacheEntry[V]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> V | None:
        """Return the cached value or None if absent / expired."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired:
                del self._store[key]
                return None
            # Move to end (most recently used)
            self._store.move_to_end(key)
            return entry.value

    async def set(self, key: str, value: V, ttl: float | None = None) -> None:
        """Insert or update a cache entry."""
        if ttl is None:
            ttl = self._default_ttl
        async with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = CacheEntry(value, ttl)
            # Evict LRU if over capacity
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)

    async def delete(self, key: str) -> None:
        """Remove an entry by key."""
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        """Remove all entries."""
        async with self._lock:
            self._store.clear()

    async def size(self) -> int:
        """Return the number of entries (including possibly-expired ones)."""
        async with self._lock:
            return len(self._store)

    async def purge_expired(self) -> int:
        """Remove expired entries. Returns the number removed."""
        now = time.monotonic()
        async with self._lock:
            expired_keys = [k for k, e in self._store.items() if e.expires_at <= now]
            for k in expired_keys:
                del self._store[k]
            return len(expired_keys)

    @property
    def maxsize(self) -> int:
        return self._maxsize

    @property
    def default_ttl(self) -> float:
        return self._default_ttl


# Application-level cache instances (created lazily at startup)
_metadata_cache: TTLCache[Any] | None = None
_address_cache: TTLCache[Any] | None = None
_results_cache: TTLCache[Any] | None = None


def get_metadata_cache() -> TTLCache[Any]:
    global _metadata_cache
    if _metadata_cache is None:
        _metadata_cache = TTLCache(maxsize=64, default_ttl=3600.0)
    return _metadata_cache


def get_address_cache() -> TTLCache[Any]:
    global _address_cache
    if _address_cache is None:
        _address_cache = TTLCache(maxsize=256, default_ttl=600.0)
    return _address_cache


def get_results_cache() -> TTLCache[Any]:
    global _results_cache
    if _results_cache is None:
        _results_cache = TTLCache(maxsize=128, default_ttl=120.0)
    return _results_cache

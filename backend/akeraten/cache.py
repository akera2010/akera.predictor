"""Cache layer: Redis when REDIS_URL is set (and the redis package is installed),
otherwise a thread-safe in-memory TTL cache."""
from __future__ import annotations

import json
import threading
import time
from typing import Any

from .config import env


class MemoryTTLCache:
    backend = "memory"

    def __init__(self, max_items: int = 5000):
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self.max_items = max_items

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            exp, val = item
            if exp and exp < time.time():
                self._data.pop(key, None)
                return None
            return val

    def set(self, key: str, value: Any, ttl: float = 60) -> None:
        with self._lock:
            if len(self._data) >= self.max_items:
                now = time.time()
                for k in [k for k, (e, _) in self._data.items() if e and e < now]:
                    self._data.pop(k, None)
                if len(self._data) >= self.max_items:
                    self._data.pop(next(iter(self._data)))
            self._data[key] = (time.time() + ttl if ttl else 0, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class RedisCache:
    backend = "redis"

    def __init__(self, url: str):
        import redis  # type: ignore

        self._r = redis.Redis.from_url(url, socket_timeout=2)
        self._r.ping()

    def get(self, key: str) -> Any | None:
        raw = self._r.get(f"akeraten:{key}")
        return None if raw is None else json.loads(raw)

    def set(self, key: str, value: Any, ttl: float = 60) -> None:
        self._r.set(f"akeraten:{key}", json.dumps(value, default=str), ex=max(1, int(ttl)) if ttl else None)

    def delete(self, key: str) -> None:
        self._r.delete(f"akeraten:{key}")

    def clear(self) -> None:  # pragma: no cover
        for k in self._r.scan_iter("akeraten:*"):
            self._r.delete(k)


_cache = None


def get_cache():
    global _cache
    if _cache is None:
        url = env("REDIS_URL")
        if url:
            try:
                _cache = RedisCache(url)
            except Exception:
                _cache = MemoryTTLCache()
        else:
            _cache = MemoryTTLCache()
    return _cache

"""Base HTTP client: env-based credentials, token-bucket rate limiting,
exponential backoff with jitter (honours Retry-After) and response caching."""
from __future__ import annotations

import logging
import random
import threading
import time
from typing import Any

import httpx

from ..cache import get_cache
from ..config import env
from .schema import now_iso

log = logging.getLogger("akeraten.ingestion")


class RateLimiter:
    def __init__(self, per_minute: float):
        self.capacity = max(1.0, per_minute)
        self.tokens = self.capacity
        self.rate = per_minute / 60.0
        self.updated = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self, max_wait: float = 10.0) -> bool:
        deadline = time.monotonic() + max_wait
        while True:
            with self.lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return True
                wait = (1 - self.tokens) / self.rate if self.rate else max_wait
            if time.monotonic() + wait > deadline:
                return False
            time.sleep(min(wait, 1.0))


class SourceError(Exception):
    pass


class BaseClient:
    name = "base"
    sports: tuple[str, ...] = ("tennis",)
    env_keys: tuple[str, ...] = ()
    base_url = ""
    rate_limit_per_min = 30
    cache_ttl = 25.0
    max_retries = 4
    provides_odds = False
    provides_scores = True

    def __init__(self, http: httpx.Client | None = None):
        self.status = "disabled" if not self.enabled else "idle"
        self.last_error: str | None = None
        self.last_fetch: str | None = None
        self.last_count = 0
        self.limiter = RateLimiter(self.rate_limit_per_min)
        self._http = http
        self.cache = get_cache()

    # ---------------------------------------------------------------- config
    def key(self, name: str | None = None) -> str | None:
        return env(name or (self.env_keys[0] if self.env_keys else ""))

    @property
    def enabled(self) -> bool:
        return bool(self.env_keys) and all(env(k) for k in self.env_keys)

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=15.0, headers={"User-Agent": "AKERATEN/0.1 (+value monitor)"})
        return self._http

    # ---------------------------------------------------------------- http
    def request(self, method: str, url: str, *, params=None, headers=None, json=None, data=None,
                cache_ttl: float | None = None) -> Any:
        ttl = self.cache_ttl if cache_ttl is None else cache_ttl
        ck = f"{self.name}:{method}:{url}:{sorted((params or {}).items())}:{json}"
        if method == "GET" and ttl:
            hit = self.cache.get(ck)
            if hit is not None:
                return hit
        delay = 1.0
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            if not self.limiter.acquire():
                raise SourceError("rate limit budget exhausted")
            try:
                r = self.http.request(method, url, params=params, headers=headers, json=json, data=data)
                if r.status_code == 429 or r.status_code >= 500:
                    ra = r.headers.get("Retry-After")
                    wait = float(ra) if ra and ra.replace(".", "", 1).isdigit() else delay
                    raise SourceError(f"HTTP {r.status_code}", wait)
                if r.status_code >= 400:
                    raise SourceError(f"HTTP {r.status_code}: {r.text[:200]}")
                body = r.json() if "json" in r.headers.get("content-type", "") or r.text[:1] in "[{" else r.text
                if method == "GET" and ttl:
                    self.cache.set(ck, body, ttl)
                return body
            except (httpx.TransportError, SourceError) as e:
                last_exc = e
                retryable = isinstance(e, httpx.TransportError) or (isinstance(e, SourceError) and len(e.args) > 1)
                if not retryable or attempt == self.max_retries:
                    break
                wait = e.args[1] if isinstance(e, SourceError) else delay
                time.sleep(min(30.0, wait) + random.uniform(0, 0.3 * delay))
                delay *= 2
        raise SourceError(str(last_exc))

    # ---------------------------------------------------------------- api
    def fetch_raw(self) -> list:
        raise NotImplementedError

    def normalize(self, item: dict) -> dict | None:
        raise NotImplementedError

    def fetch(self) -> list[dict]:
        if not self.enabled:
            self.status = "disabled"
            return []
        try:
            raw = self.fetch_raw() or []
            out = []
            for item in raw:
                try:
                    m = self.normalize(item)
                except Exception as e:  # noqa: BLE001 - one bad item must not kill the batch
                    log.debug("%s: cannot normalise item: %s", self.name, e)
                    m = None
                if m:
                    out.append(m)
            self.status, self.last_error = "ok", None
            self.last_count = len(out)
            self.last_fetch = now_iso()
            return out
        except Exception as e:  # noqa: BLE001
            self.status, self.last_error = "error", str(e)[:300]
            log.warning("%s fetch failed: %s", self.name, e)
            return []

    def info(self) -> dict:
        return {"name": self.name, "enabled": self.enabled, "status": self.status, "sports": list(self.sports),
                "last_fetch": self.last_fetch, "last_error": self.last_error, "matches": self.last_count}

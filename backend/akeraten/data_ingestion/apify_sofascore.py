"""Apify SofaScore scraper (tennis + table tennis). Runs an Apify actor synchronously
and reads its dataset. Actor id configurable via APIFY_SOFASCORE_ACTOR; items are
expected in SofaScore event format (see sofascore_format.py)."""
from __future__ import annotations

from ..config import env
from .base import BaseClient
from .sofascore_format import sofascore_event


class ApifySofascoreClient(BaseClient):
    name = "apify_sofascore"
    sports = ("tennis", "table_tennis")
    env_keys = ("APIFY_TOKEN",)
    rate_limit_per_min = 6
    cache_ttl = 60

    def fetch_raw(self) -> list:
        actor = env("APIFY_SOFASCORE_ACTOR", "azzouzana~sofascore-scraper-pro")
        url = f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
        body = self.request("POST", url, params={"token": self.key(), "timeout": 60},
                            json={"sports": ["tennis", "table-tennis"], "live": True})
        return body if isinstance(body, list) else []

    def normalize(self, it: dict) -> dict | None:
        return sofascore_event(it.get("event", it), self.name, "sofa")

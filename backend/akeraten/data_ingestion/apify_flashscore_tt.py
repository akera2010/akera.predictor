"""Apify Flashscore table-tennis scraper. Actor id via APIFY_FLASHSCORE_TT_ACTOR.

ASSUMED item shape: {"matchId","homeName","awayName","tournament","status",
"homeScore","awayScore","sets":[{"home":11,"away":8}],"odds":{"home":1.6,"away":2.3},
"startTime"}"""
from __future__ import annotations

from ..config import env
from .base import BaseClient
from .schema import make_match
from .sportradar_tt import _category


class ApifyFlashscoreTTClient(BaseClient):
    name = "apify_flashscore_tt"
    sports = ("table_tennis",)
    env_keys = ("APIFY_TOKEN",)
    rate_limit_per_min = 6
    cache_ttl = 60

    def fetch_raw(self) -> list:
        actor = env("APIFY_FLASHSCORE_TT_ACTOR", "statanow~flashscore-scraper-live")
        url = f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
        body = self.request("POST", url, params={"token": self.key(), "timeout": 60},
                            json={"sport": "table-tennis", "live": True})
        return body if isinstance(body, list) else []

    def normalize(self, it: dict) -> dict | None:
        sets = [[s.get("home", 0), s.get("away", 0)] for s in it.get("sets") or []]
        status = it.get("status")
        live = str(status).lower() in ("live", "inprogress", "in progress")
        odds = it.get("odds") or {}
        return make_match("table_tennis", f"fs-{it.get('matchId')}", it.get("homeName"), it.get("awayName"),
                          it.get("tournament"), None, status,
                          {"sets": sets, "games": [it.get("homeScore", 0), it.get("awayScore", 0)],
                           "points": f"{sets[-1][0]}-{sets[-1][1]}" if live and sets else None},
                          {"player_a": odds.get("home"), "player_b": odds.get("away")}, source=self.name,
                          category=_category(it.get("tournament")), start_time=it.get("startTime"))

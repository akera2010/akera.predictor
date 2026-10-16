"""LiveTennisAPI client (tennis live scores).

ASSUMED payload shape (verify against your plan's docs and adapt `normalize`):
GET {LIVETENNISAPI_BASE_URL}/matches/live  (header X-API-Key)
-> {"matches":[{"id":..,"home":{"name":..,"rank":..,"country":..},"away":{...},
     "tournament":{"name":..,"surface":..,"category":"ATP"},"status":"live",
     "score":{"sets":[{"home":6,"away":4},{"home":3,"away":2}],
              "points":{"home":"30","away":"15"},"server":"home"},
     "odds":{"home":1.85,"away":2.05},"start_time":"2026-..Z","best_of":3}]}
"""
from __future__ import annotations

from ..config import env
from .base import BaseClient
from .schema import make_match


class LiveTennisAPIClient(BaseClient):
    name = "livetennisapi"
    sports = ("tennis",)
    env_keys = ("LIVETENNISAPI_KEY",)
    rate_limit_per_min = 30

    @property
    def base(self) -> str:
        return env("LIVETENNISAPI_BASE_URL", "https://api.livetennisapi.com/v1")

    def fetch_raw(self) -> list:
        h = {"X-API-Key": self.key()}
        out = []
        for path in ("/matches/live", "/matches/upcoming"):
            body = self.request("GET", self.base + path, headers=h)
            out += body.get("matches", body if isinstance(body, list) else []) if isinstance(body, (dict, list)) else []
        return out

    def normalize(self, it: dict) -> dict | None:
        home, away = it.get("home") or {}, it.get("away") or {}
        t = it.get("tournament") or {}
        sc = it.get("score") or {}
        sets = [[s.get("home", 0), s.get("away", 0)] for s in sc.get("sets", [])]
        pts = sc.get("points") or {}
        points = f"{pts.get('home')}-{pts.get('away')}" if pts.get("home") is not None else None
        srv = {"home": "a", "away": "b"}.get(sc.get("server"))
        odds = it.get("odds") or {}
        return make_match("tennis", f"lta-{it.get('id')}", home.get("name"), away.get("name"), t.get("name"),
                          t.get("surface"), it.get("status"),
                          {"sets": sets, "games": sets[-1] if sets else [], "points": points},
                          {"player_a": odds.get("home"), "player_b": odds.get("away")}, source=self.name,
                          category=t.get("category"), server=srv, rank_a=home.get("rank"), rank_b=away.get("rank"),
                          country_a=home.get("country"), country_b=away.get("country"),
                          start_time=it.get("start_time"), best_of=it.get("best_of"))

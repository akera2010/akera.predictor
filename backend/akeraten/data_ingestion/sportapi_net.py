"""SportAPI (sportapi.net style REST) client. Base URL via SPORTAPI_BASE_URL.

ASSUMED payload: GET {base}/live?sport=tennis|table-tennis (header x-api-key)
-> {"data":[{"id","sport","league":{"name","category"},"participants":
[{"name","side":"home","rank","country"}],"status","scores":{"periods":[[6,4],[3,2]],
"current":[1,0],"points":"30-15","serving":"home"},"odds":{"home","away"},"start"}]}"""
from __future__ import annotations

from ..config import env
from .base import BaseClient
from .schema import make_match


class SportAPINetClient(BaseClient):
    name = "sportapi_net"
    sports = ("tennis", "table_tennis")
    env_keys = ("SPORTAPI_KEY",)
    rate_limit_per_min = 30

    def fetch_raw(self) -> list:
        base = env("SPORTAPI_BASE_URL", "https://api.sportapi.net/v1")
        out = []
        for sport in ("tennis", "table-tennis"):
            body = self.request("GET", f"{base}/live", params={"sport": sport}, headers={"x-api-key": self.key()})
            out += body.get("data", []) if isinstance(body, dict) else []
        return out

    def normalize(self, it: dict) -> dict | None:
        parts = it.get("participants") or []
        home = next((p for p in parts if p.get("side") == "home"), parts[0] if parts else {})
        away = next((p for p in parts if p.get("side") == "away"), parts[1] if len(parts) > 1 else {})
        sc = it.get("scores") or {}
        sport = it.get("sport")
        periods = sc.get("periods") or []
        tt = "table" in str(sport)
        lg = it.get("league") or {}
        odds = it.get("odds") or {}
        return make_match(sport, f"sapi-{it.get('id')}", home.get("name"), away.get("name"), lg.get("name"),
                          it.get("surface"), it.get("status"),
                          {"sets": periods, "games": sc.get("current") if tt else (periods[-1] if periods else []),
                           "points": sc.get("points")},
                          {"player_a": odds.get("home"), "player_b": odds.get("away")}, source=self.name,
                          category=lg.get("category"), server={"home": "a", "away": "b"}.get(sc.get("serving")),
                          rank_a=home.get("rank"), rank_b=away.get("rank"), country_a=home.get("country"),
                          country_b=away.get("country"), start_time=it.get("start"))

"""The Odds API v4 (odds only; tennis). https://the-odds-api.com
GET /v4/sports?apiKey=  -> active sport keys (group "Tennis")
GET /v4/sports/{key}/odds?apiKey=&regions=eu&markets=h2h&oddsFormat=decimal
Each request costs credits, hence the long cache TTL."""
from __future__ import annotations

from datetime import datetime, timezone

from ..config import env
from .base import BaseClient
from .schema import make_match

PREFERRED = ("pinnacle", "betfair_ex_eu", "bet365", "williamhill", "unibet_eu", "marathonbet")


class TheOddsAPIClient(BaseClient):
    name = "the_odds_api"
    sports = ("tennis",)
    env_keys = ("ODDS_API_KEY",)
    rate_limit_per_min = 10
    cache_ttl = 120
    provides_odds = True
    provides_scores = False
    base = "https://api.the-odds-api.com/v4"

    def fetch_raw(self) -> list:
        sports = self.request("GET", f"{self.base}/sports", params={"apiKey": self.key()}, cache_ttl=3600)
        keys = [s["key"] for s in sports if isinstance(s, dict) and s.get("group") == "Tennis" and s.get("active")]
        out = []
        for k in keys[:8]:
            out += self.request("GET", f"{self.base}/sports/{k}/odds",
                                params={"apiKey": self.key(), "regions": env("ODDS_API_REGIONS", "eu"),
                                        "markets": "h2h", "oddsFormat": "decimal"}) or []
        return out

    def normalize(self, ev: dict) -> dict | None:
        home, away = ev.get("home_team"), ev.get("away_team")
        best = {}
        books = sorted(ev.get("bookmakers") or [], key=lambda b: PREFERRED.index(b["key"]) if b.get("key") in PREFERRED else 99)
        for bk in books:
            for mk in bk.get("markets", []):
                if mk.get("key") != "h2h":
                    continue
                prices = {o["name"]: o["price"] for o in mk.get("outcomes", [])}
                if home in prices and away in prices:
                    best = {"player_a": prices[home], "player_b": prices[away], "bookmaker": bk.get("title")}
                    break
            if best:
                break
        ct = ev.get("commence_time")
        status = "upcoming"
        try:
            if ct and datetime.fromisoformat(ct.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                status = "live"
        except ValueError:
            pass
        title = (ev.get("sport_title") or "")
        cat = "WTA" if "WTA" in title else "ATP" if "ATP" in title else None
        return make_match("tennis", f"odds-{ev.get('id')}", home, away, title, None, status, None, best,
                          source=self.name, category=cat, start_time=ct, bookmaker=best.get("bookmaker"))

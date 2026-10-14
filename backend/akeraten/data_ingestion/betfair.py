"""Betfair Exchange (API-NG) client: odds (best available back prices).

Login: POST https://identitysso.betfair.com/api/login (X-Application, username, password)
Then JSON-RPC https://api.betfair.com/exchange/betting/json-rpc/v1
  SportsAPING/v1.0/listMarketCatalogue  (MATCH_ODDS, eventTypeIds tennis=2)
  SportsAPING/v1.0/listMarketBook       (EX_BEST_OFFERS)
Exchange prices are before commission (typically 2-5%)."""
from __future__ import annotations

import time

from ..config import env
from .base import BaseClient, SourceError
from .schema import make_match

RPC = "https://api.betfair.com/exchange/betting/json-rpc/v1"


class BetfairClient(BaseClient):
    name = "betfair"
    sports = ("tennis", "table_tennis")
    env_keys = ("BETFAIR_USERNAME", "BETFAIR_PASSWORD", "BETFAIR_APP_KEY")
    rate_limit_per_min = 20
    cache_ttl = 10
    provides_odds = True
    provides_scores = False

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._token, self._token_ts = None, 0.0

    def _login(self) -> str:
        if self._token and time.time() - self._token_ts < 3 * 3600:
            return self._token
        body = self.request("POST", "https://identitysso.betfair.com/api/login",
                            headers={"X-Application": self.key("BETFAIR_APP_KEY"), "Accept": "application/json"},
                            data={"username": self.key("BETFAIR_USERNAME"), "password": self.key("BETFAIR_PASSWORD")},
                            cache_ttl=0)
        if not isinstance(body, dict) or body.get("status") != "SUCCESS":
            raise SourceError(f"betfair login failed: {body.get('error') if isinstance(body, dict) else body}")
        self._token, self._token_ts = body["token"], time.time()
        return self._token

    def _rpc(self, method: str, params: dict):
        h = {"X-Application": self.key("BETFAIR_APP_KEY"), "X-Authentication": self._login(),
             "Content-Type": "application/json"}
        body = self.request("POST", RPC, headers=h, json={"jsonrpc": "2.0", "method": f"SportsAPING/v1.0/{method}",
                                                         "params": params, "id": 1}, cache_ttl=0)
        if isinstance(body, dict) and "error" in body:
            raise SourceError(str(body["error"]))
        return body.get("result", []) if isinstance(body, dict) else []

    def fetch_raw(self) -> list:
        types = {"2": "tennis"}
        tt_type = env("BETFAIR_TT_EVENT_TYPE")  # set if your account lists table tennis
        if tt_type:
            types[tt_type] = "table_tennis"
        out = []
        for et, sport in types.items():
            cats = self._rpc("listMarketCatalogue", {
                "filter": {"eventTypeIds": [et], "marketTypeCodes": ["MATCH_ODDS"], "inPlayOnly": False},
                "maxResults": 100, "marketProjection": ["RUNNER_DESCRIPTION", "EVENT", "COMPETITION",
                                                        "MARKET_START_TIME"]})
            if not cats:
                continue
            books = {b["marketId"]: b for b in self._rpc("listMarketBook", {
                "marketIds": [c["marketId"] for c in cats][:40],
                "priceProjection": {"priceData": ["EX_BEST_OFFERS"]}})}
            for c in cats:
                if c["marketId"] in books:
                    out.append({"catalogue": c, "book": books[c["marketId"]], "sport": sport})
        return out

    def normalize(self, it: dict) -> dict | None:
        c, b = it["catalogue"], it["book"]
        runners = c.get("runners") or []
        if len(runners) != 2:
            return None
        prices = {}
        for r in b.get("runners", []):
            backs = (r.get("ex") or {}).get("availableToBack") or []
            if backs:
                prices[r["selectionId"]] = backs[0]["price"]
        ra, rb = runners
        return make_match(it["sport"], f"bf-{c['marketId']}", ra["runnerName"], rb["runnerName"],
                          (c.get("competition") or {}).get("name"), None,
                          "live" if b.get("inplay") else ("finished" if b.get("status") == "CLOSED" else "upcoming"),
                          None, {"player_a": prices.get(ra["selectionId"]), "player_b": prices.get(rb["selectionId"])},
                          source=self.name, start_time=c.get("marketStartTime"), bookmaker="Betfair Exchange")

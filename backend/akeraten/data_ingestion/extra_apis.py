"""Loader for user-defined sources in extra_apis.json.

Schema (list of objects):
{"name": "my_feed", "base_url": "https://host/api/live", "sport": ["tennis"],
 "rate_limit": 30,                                   # requests per minute
 "auth": {"type": "header"|"query"|"bearer"|"none", "name": "X-Api-Key", "env": "MY_FEED_KEY"},
 "items_path": "data.events",                        # optional dotted path to the list
 "mapping": {"match_id": "id", "player_a": "home.name", "player_b": "away.name",
             "tournament": "league.name", "surface": "surface", "status": "status",
             "sets": "score.sets", "points": "score.points",
             "odds_a": "odds.home", "odds_b": "odds.away"}}
Keys are always read from the environment variable named in auth.env."""
from __future__ import annotations

import json
from pathlib import Path

from ..config import BACKEND_DIR, env
from .base import BaseClient
from .schema import get_path, make_match

EXTRA_APIS_PATH = BACKEND_DIR / "akeraten" / "data_ingestion" / "extra_apis.json"
DEFAULT_MAP = {"match_id": "id", "player_a": "player_a", "player_b": "player_b", "tournament": "tournament",
               "surface": "surface", "status": "status", "sets": "score.sets", "points": "score.points",
               "odds_a": "odds.player_a", "odds_b": "odds.player_b"}


class GenericClient(BaseClient):
    def __init__(self, spec: dict, **kw):
        self.spec = spec
        self.name = spec["name"]
        self.sports = tuple(spec.get("sport") or ["tennis"])
        self.rate_limit_per_min = float(spec.get("rate_limit", 30))
        auth = spec.get("auth") or {}
        self.env_keys = (auth["env"],) if auth.get("env") else ()
        super().__init__(**kw)

    @property
    def enabled(self) -> bool:
        auth = self.spec.get("auth") or {}
        if auth.get("type", "none") == "none":
            return True
        return bool(auth.get("env") and env(auth["env"]))

    def fetch_raw(self) -> list:
        auth = self.spec.get("auth") or {}
        headers, params = {}, {}
        key = env(auth.get("env", "")) if auth.get("env") else None
        t = auth.get("type", "none")
        if t == "header":
            headers[auth.get("name", "X-API-Key")] = key
        elif t == "query":
            params[auth.get("name", "apikey")] = key
        elif t == "bearer":
            headers["Authorization"] = f"Bearer {key}"
        body = self.request("GET", self.spec["base_url"], params=params, headers=headers)
        items = get_path(body, self.spec["items_path"]) if self.spec.get("items_path") else body
        return items if isinstance(items, list) else []

    def normalize(self, it: dict) -> dict | None:
        mp = {**DEFAULT_MAP, **(self.spec.get("mapping") or {})}
        g = lambda k: get_path(it, mp[k]) if mp.get(k) else None  # noqa: E731
        sets = g("sets") or []
        return make_match(it.get("sport") or self.sports[0], f"{self.name}-{g('match_id')}", g("player_a"),
                          g("player_b"), g("tournament"), g("surface"), g("status"),
                          {"sets": sets, "games": sets[-1] if sets else [], "points": g("points")},
                          {"player_a": g("odds_a"), "player_b": g("odds_b")}, source=self.name)


def load_extra_apis(path: Path | str = EXTRA_APIS_PATH) -> list[GenericClient]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        specs = json.loads(p.read_text())
    except json.JSONDecodeError:
        return []
    out = []
    for s in specs if isinstance(specs, list) else []:
        if isinstance(s, dict) and s.get("name") and s.get("base_url"):
            out.append(GenericClient(s))
    return out

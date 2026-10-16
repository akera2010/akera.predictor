"""Sportradar Table Tennis v2 client.

GET https://api.sportradar.com/table-tennis/{SPORTRADAR_TT_ACCESS}/v2/{lang}/schedules/live/summaries.json
(header x-api-key). Payload: {"summaries":[{"sport_event":{"id","start_time",
"sport_event_context":{"competition":{"name"}},"competitors":[{"name":"Wang, Chuqin",
"qualifier":"home","country_code"}]},"sport_event_status":{"status":"live",
"home_score":1,"away_score":0,"period_scores":[{"home_score":11,"away_score":8}]}}]}
"""
from __future__ import annotations

from ..config import env
from .base import BaseClient
from .schema import make_match


def _pretty(name: str | None) -> str | None:
    """Sportradar uses 'Surname, Name'. East-Asian names keep surname first."""
    if not name or "," not in name:
        return name
    last, first = [x.strip() for x in name.split(",", 1)]
    return f"{last} {first}" if _asian(last) else f"{first} {last}"


def _asian(surname: str) -> bool:
    return surname.lower() in {"wang", "lin", "fan", "liang", "sun", "chen", "kuai", "zhou", "xiang", "ma", "zhang",
                               "liu", "li", "wu", "he", "qian", "cheng", "shin", "jang", "lim", "joo"}


class SportradarTTClient(BaseClient):
    name = "sportradar_tt"
    sports = ("table_tennis",)
    env_keys = ("SPORTRADAR_TT_KEY",)
    rate_limit_per_min = 50

    def fetch_raw(self) -> list:
        access = env("SPORTRADAR_TT_ACCESS", "trial")
        url = f"https://api.sportradar.com/table-tennis/{access}/v2/en/schedules/live/summaries.json"
        body = self.request("GET", url, headers={"x-api-key": self.key()})
        return body.get("summaries", []) if isinstance(body, dict) else []

    def normalize(self, it: dict) -> dict | None:
        ev = it.get("sport_event") or {}
        st = it.get("sport_event_status") or {}
        comps = ev.get("competitors") or []
        home = next((c for c in comps if c.get("qualifier") == "home"), comps[0] if comps else {})
        away = next((c for c in comps if c.get("qualifier") == "away"), comps[1] if len(comps) > 1 else {})
        periods = [[p.get("home_score", 0), p.get("away_score", 0)] for p in st.get("period_scores", [])]
        cur = periods[-1] if periods else [0, 0]
        comp = (ev.get("sport_event_context") or {}).get("competition") or {}
        status = st.get("status")
        return make_match("table_tennis", f"sr-{ev.get('id')}", _pretty(home.get("name")), _pretty(away.get("name")),
                          comp.get("name"), None, "live" if status in ("live", "inprogress") else status,
                          {"sets": periods, "games": [st.get("home_score", 0), st.get("away_score", 0)],
                           "points": f"{cur[0]}-{cur[1]}" if status in ("live", "inprogress") else None},
                          None, source=self.name, category=_category(comp.get("name")),
                          country_a=home.get("country_code"), country_b=away.get("country_code"),
                          start_time=ev.get("start_time"))


def _category(name: str | None) -> str | None:
    n = (name or "").lower()
    if "wtt" in n:
        return "WTT"
    if "ittf" in n or "world" in n:
        return "ITTF"
    if "setka" in n:
        return "Setka Cup"
    if "elite" in n:
        return "TT Elite Series"
    if "liga pro" in n:
        return "Czech Liga Pro"
    return None

"""Shared normaliser for SofaScore-style event JSON (used by the Apify SofaScore
actor and by several RapidAPI tennis/TT feeds that mirror that format)."""
from __future__ import annotations

from .schema import make_match

TT_SLUGS = {"table-tennis", "table_tennis", "tabletennis"}


def sofascore_event(ev: dict, source: str, prefix: str) -> dict | None:
    sport = ((ev.get("tournament") or {}).get("category") or {}).get("sport", {}).get("slug") or ev.get("sport") or "tennis"
    sport = "table_tennis" if str(sport).lower() in TT_SLUGS else "tennis"
    hs, as_ = ev.get("homeScore") or {}, ev.get("awayScore") or {}
    sets = []
    for i in range(1, 8):
        k = f"period{i}"
        if k in hs or k in as_:
            sets.append([hs.get(k, 0) or 0, as_.get(k, 0) or 0])
    status = (ev.get("status") or {}).get("type") or ev.get("status")
    live = str(status).lower() in ("inprogress", "live")
    points = f"{hs.get('point')}-{as_.get('point')}" if live and hs.get("point") is not None else None
    if sport == "table_tennis":
        games = [hs.get("current", 0) or 0, as_.get("current", 0) or 0]
        if live and sets:
            points = f"{sets[-1][0]}-{sets[-1][1]}"
    else:
        games = sets[-1] if (sets and live) else []
    t = ev.get("tournament") or {}
    cat = (t.get("category") or {}).get("name")
    srv = {1: "a", 2: "b"}.get(ev.get("firstToServe"))  # SofaScore: server of the current game
    home, away = ev.get("homeTeam") or {}, ev.get("awayTeam") or {}
    odds = ev.get("odds") or {}
    return make_match(sport, f"{prefix}-{ev.get('id')}", home.get("name"), away.get("name"), t.get("name"),
                      ev.get("groundType"), status, {"sets": sets, "games": games, "points": points},
                      {"player_a": odds.get("home"), "player_b": odds.get("away")}, source=source,
                      category=_cat(cat, t.get("name")), server=srv if live else None,
                      rank_a=home.get("ranking"), rank_b=away.get("ranking"),
                      country_a=(home.get("country") or {}).get("alpha3"),
                      country_b=(away.get("country") or {}).get("alpha3"),
                      start_time=ev.get("startTimestamp"))


def _cat(cat: str | None, tname: str | None) -> str | None:
    s = f"{cat or ''} {tname or ''}".lower()
    for key, label in (("challenger", "Challenger"), ("itf", "ITF"), ("wta", "WTA"), ("atp", "ATP"),
                       ("wtt", "WTT"), ("ittf", "ITTF"), ("setka", "Setka Cup"), ("elite", "TT Elite Series"),
                       ("liga pro", "Czech Liga Pro")):
        if key in s:
            return label
    return cat

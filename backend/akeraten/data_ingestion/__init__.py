"""Data ingestion: one client per provider + the demo simulator + merging."""
from __future__ import annotations

from ..names import keys
from .apify_flashscore_tt import ApifyFlashscoreTTClient
from .apify_sofascore import ApifySofascoreClient
from .base import BaseClient
from .betfair import BetfairClient
from .demo import DemoProvider
from .extra_apis import load_extra_apis
from .livetennisapi import LiveTennisAPIClient
from .sportapi_net import SportAPINetClient
from .sportmicro import SportMicroClient
from .sportradar_tt import SportradarTTClient
from .the_odds_api import TheOddsAPIClient

CLIENT_CLASSES = [LiveTennisAPIClient, SportradarTTClient, ApifyFlashscoreTTClient, ApifySofascoreClient,
                  SportMicroClient, SportAPINetClient, TheOddsAPIClient, BetfairClient]


def build_clients() -> list[BaseClient]:
    return [cls() for cls in CLIENT_CLASSES] + load_extra_apis()


def _pair_key(m: dict) -> tuple[str, frozenset, frozenset]:
    return m["sport"], frozenset(keys(m["player_a"])), frozenset(keys(m["player_b"]))


def merge_matches(batches: list[list[dict]]) -> list[dict]:
    """Merge the same match reported by several sources (score from score feeds,
    odds from odds feeds). Earlier batches have priority for each field."""
    merged: list[dict] = []
    for batch in batches:
        for m in batch:
            sport, ka, kb = _pair_key(m)
            target, swapped = None, False
            for g in merged:
                gs, ga, gb = _pair_key(g)
                if gs != sport:
                    continue
                if ga & ka and gb & kb:
                    target = g
                    break
                if ga & kb and gb & ka:
                    target, swapped = g, True
                    break
            if target is None:
                merged.append(dict(m, sources=[m.get("source")]))
                continue
            target.setdefault("sources", []).append(m.get("source"))
            if not target.get("odds") and m.get("odds"):
                o = m["odds"]
                target["odds"] = {"player_a": o["player_b"], "player_b": o["player_a"]} if swapped else o
                target["bookmaker"] = m.get("bookmaker") or m.get("source")
            if target.get("status") == "upcoming" and m.get("status") in ("live", "finished") and m.get("score", {}).get("sets"):
                target["status"] = m["status"]
                target["score"] = m["score"]
            for k, v in m.items():
                if k not in target or target[k] in (None, "", [], {}):
                    target[k] = v
    return merged


__all__ = ["DemoProvider", "build_clients", "merge_matches", "CLIENT_CLASSES"]

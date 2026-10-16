"""Common match schema shared by every data source.

{"sport":"tennis"|"table_tennis","match_id","player_a","player_b","tournament",
 "surface":"hard"|"clay"|"grass"|"indoor"|None,"status":"live"|"upcoming"|"finished",
 "score":{"sets":[[6,4],[3,2]],"games":[3,2],"points":"30-15"},
 "odds":{"player_a":1.85,"player_b":2.05},"timestamp":ISO8601, "source": "<client>"}

Tennis: score.sets lists every set incl. the one in progress, score.games is the
current set. Table tennis: score.sets lists every game's points incl. the current
one, score.games = games won [a, b], score.points = current game points.
"""
from __future__ import annotations

from datetime import datetime, timezone

LIVE_WORDS = {"live", "inprogress", "in_progress", "in progress", "playing", "started", "1st set", "2nd set",
              "3rd set", "4th set", "5th set", "interrupted", "en juego", "en vivo", "directo"}
FINISHED_WORDS = {"finished", "ended", "closed", "complete", "completed", "ft", "final", "retired", "walkover",
                  "aet", "finalizado", "terminado", "cancelled", "canceled", "abandoned"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def norm_status(s) -> str:
    v = str(s or "").strip().lower()
    if v in FINISHED_WORDS or "finish" in v or "ended" in v or "closed" in v:
        return "finished"
    if v in LIVE_WORDS or "live" in v or "progress" in v or "set" in v:
        return "live"
    return "upcoming"


def norm_surface(s) -> str | None:
    v = str(s or "").strip().lower()
    if not v:
        return None
    if "indoor" in v or "carpet" in v or "cubierta" in v:
        return "indoor"
    if "clay" in v or "arcilla" in v or "tierra" in v:
        return "clay"
    if "grass" in v or "hierba" in v or "césped" in v or "cesped" in v:
        return "grass"
    if "hard" in v or "dura" in v or "acrylic" in v:
        return "hard"
    return None


def norm_sport(s) -> str:
    v = str(s or "").lower().replace("-", "_").replace(" ", "_")
    return "table_tennis" if ("table" in v or v in ("tt", "ping_pong", "pingpong", "tenis_de_mesa")) else "tennis"


def _odd(x) -> float | None:
    try:
        v = float(x)
        return round(v, 3) if v > 1.0 else None
    except (TypeError, ValueError):
        return None


def make_match(sport, match_id, player_a, player_b, tournament=None, surface=None, status=None,
               score=None, odds=None, timestamp=None, source="unknown", **extra) -> dict | None:
    if not player_a or not player_b or match_id in (None, ""):
        return None
    sport = norm_sport(sport)
    sc = score or {}
    m = {
        "sport": sport,
        "match_id": str(match_id),
        "player_a": str(player_a).strip(),
        "player_b": str(player_b).strip(),
        "tournament": tournament,
        "surface": norm_surface(surface) if sport == "tennis" else None,
        "status": norm_status(status),
        "score": {"sets": [list(map(int, s)) for s in (sc.get("sets") or [])],
                  "games": list(sc.get("games") or []), "points": sc.get("points")},
        "odds": None,
        "timestamp": timestamp or now_iso(),
        "source": source,
    }
    for k in ("tiebreak", "sets_won"):
        if k in sc:
            m["score"][k] = sc[k]
    oa, ob = _odd((odds or {}).get("player_a")), _odd((odds or {}).get("player_b"))
    if oa and ob:
        m["odds"] = {"player_a": oa, "player_b": ob}
    st = extra.get("start_time")
    if isinstance(st, (int, float)):
        extra["start_time"] = datetime.fromtimestamp(st, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    m.update({k: v for k, v in extra.items() if v is not None})
    for k in ("category", "start_time", "best_of", "server", "rank_a", "rank_b", "country_a", "country_b"):
        m.setdefault(k, None)
    if m["best_of"] is None:
        m["best_of"] = 5 if sport == "table_tennis" else 3
    return m


def tennis_score_from_sets(set_pairs: list[tuple[int, int]], points: str | None = None, live: bool = True) -> dict:
    sets = [[int(a or 0), int(b or 0)] for a, b in set_pairs]
    games = sets[-1] if (sets and live) else [0, 0]
    return {"sets": sets, "games": games, "points": points}


def get_path(obj, path: str, default=None):
    """Dotted-path getter supporting list indexes: 'a.b.0.c'."""
    cur = obj
    for part in str(path).split("."):
        if cur is None:
            return default
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return default
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return default
    return default if cur is None else cur

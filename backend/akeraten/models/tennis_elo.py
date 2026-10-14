"""Surface-aware tennis Elo (FiveThirtyEight-style decaying K factor).

Ratings are trained by scripts/train_models.py and stored in data/tennis_ratings.json.
Unknown players fall back to a rating derived from their ranking (if known)."""
from __future__ import annotations

import json
import math
from pathlib import Path

from ..config import DATA_DIR
from ..names import NameIndex

SURFACES = ("hard", "clay", "grass")
DEFAULT_RATING = 1500.0
RATINGS_PATH = DATA_DIR / "tennis_ratings.json"


def norm_surface(surface: str | None) -> str | None:
    if not surface:
        return None
    s = surface.lower()
    if s in ("indoor", "carpet", "hard (indoor)", "indoor hard", "i.hard"):
        return "hard"
    if s.startswith("hard"):
        return "hard"
    if s.startswith("clay") or s in ("arcilla", "tierra batida"):
        return "clay"
    if s.startswith("grass") or s in ("hierba", "cesped", "césped"):
        return "grass"
    return None


def expected(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))


def k_factor(n: int) -> float:
    return 250.0 / ((n + 5) ** 0.4)


def rating_from_rank(rank: int | None) -> float:
    if not rank or rank <= 0:
        return DEFAULT_RATING + 50
    return max(1400.0, 2150.0 - 85.0 * math.log(rank))


class TennisElo:
    def __init__(self, players: dict | None = None, meta: dict | None = None):
        self.players: dict[str, dict] = players or {}
        self.h2h: dict[str, list] = {}
        self.meta = meta or {}
        self._index = NameIndex(self.players.keys())

    # ------------------------------------------------------------- storage
    @classmethod
    def load(cls, path: Path | str = RATINGS_PATH) -> "TennisElo":
        p = Path(path)
        if not p.exists():
            return cls()
        data = json.loads(p.read_text())
        obj = cls(data.get("players", {}), data.get("meta", {}))
        obj.h2h = data.get("h2h", {})
        return obj

    def save(self, path: Path | str = RATINGS_PATH) -> None:
        Path(path).write_text(json.dumps({"meta": self.meta, "players": self.players, "h2h": self.h2h},
                                         ensure_ascii=False, separators=(",", ":")))

    # ------------------------------------------------------------- access
    def resolve(self, name: str) -> str | None:
        return name if name in self.players else self._index.find(name)

    def player(self, name: str, rank: int | None = None) -> dict:
        key = self.resolve(name)
        if key:
            return self.players[key]
        r = rating_from_rank(rank)
        return {"elo": r, "hard": r, "clay": r, "grass": r, "n": 0, "rank": rank, "form": [], "unknown": True}

    def _ensure(self, name: str) -> dict:
        if name not in self.players:
            self.players[name] = {"elo": DEFAULT_RATING, "hard": DEFAULT_RATING, "clay": DEFAULT_RATING,
                                  "grass": DEFAULT_RATING, "n": 0, "n_hard": 0, "n_clay": 0, "n_grass": 0,
                                  "form": []}
            self._index.add(name)
        return self.players[name]

    # ------------------------------------------------------------- model
    def ratings(self, name: str, surface: str | None, rank: int | None = None) -> tuple[float, float]:
        p = self.player(name, rank)
        s = norm_surface(surface)
        return p["elo"], p.get(s, p["elo"]) if s else p["elo"]

    def predict(self, a: str, b: str, surface: str | None = None, rank_a: int | None = None,
                rank_b: int | None = None) -> dict:
        ea, sa = self.ratings(a, surface, rank_a)
        eb, sb = self.ratings(b, surface, rank_b)
        p_all = expected(ea, eb)
        p_surf = expected(sa, sb)
        blended = expected(0.5 * (ea + sa), 0.5 * (eb + sb))
        return {"prob_a": blended, "overall_prob_a": p_all, "surface_prob_a": p_surf,
                "elo_a": round(ea, 1), "elo_b": round(eb, 1), "surface_elo_a": round(sa, 1),
                "surface_elo_b": round(sb, 1),
                "known_a": not self.player(a, rank_a).get("unknown"), "known_b": not self.player(b, rank_b).get("unknown")}

    def update(self, winner: str, loser: str, surface: str | None = None) -> None:
        w, l = self._ensure(winner), self._ensure(loser)
        e = expected(w["elo"], l["elo"])
        kw, kl = k_factor(w["n"]), k_factor(l["n"])
        w["elo"] += kw * (1 - e)
        l["elo"] -= kl * (1 - e)
        w["n"] += 1
        l["n"] += 1
        s = norm_surface(surface)
        if s:
            es = expected(w.get(s, w["elo"]), l.get(s, l["elo"]))
            nw, nl = w.get(f"n_{s}", w["n"] // 3), l.get(f"n_{s}", l["n"] // 3)
            w[s] = w.get(s, w["elo"]) + k_factor(nw) * (1 - es)
            l[s] = l.get(s, l["elo"]) - k_factor(nl) * (1 - es)
            w[f"n_{s}"], l[f"n_{s}"] = nw + 1, nl + 1

    def head_to_head(self, a: str, b: str) -> dict:
        ka, kb = self.resolve(a) or a, self.resolve(b) or b
        rec = self.h2h.get(f"{ka}|{kb}")
        if rec:
            return {"a": rec[0], "b": rec[1], "last": rec[2] if len(rec) > 2 else []}
        rec = self.h2h.get(f"{kb}|{ka}")
        if rec:
            last = [dict(x, winner=("a" if x.get("winner") == "b" else "b")) for x in (rec[2] if len(rec) > 2 else [])]
            return {"a": rec[1], "b": rec[0], "last": last}
        return {"a": 0, "b": 0, "last": []}


_elo: TennisElo | None = None


def get_tennis_elo() -> TennisElo:
    global _elo
    if _elo is None:
        _elo = TennisElo.load()
    return _elo

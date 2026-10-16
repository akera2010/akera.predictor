"""Table-tennis Elo with seeded ratings for top players.

Seeds are derived from (approximate) world ranking positions, NOT from match
history, so they are a weak prior; the rating updates as results come in.
League (Setka Cup / TT Elite Series style) players start from a neutral seed."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from ..config import DATA_DIR
from ..names import NameIndex
from ..players import TT_LEAGUE, TT_MEN, TT_WOMEN
from .tennis_elo import expected

DEFAULT_RATING = 1650.0
K_BASE = 32.0
STATE_PATH = DATA_DIR / "tt_ratings.json"


def seed_from_rank(rank: int | None) -> float:
    if not rank:
        return DEFAULT_RATING
    return 2290.0 - 80.0 * math.log(rank)


def _league_seed(name: str, rating: float) -> float:
    # Leagues: we only know a rough level -> noisy prior around the true level.
    h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16) / 0xFFFFFF
    return round(1700.0 + (rating - 1700.0) * 0.5 + (h - 0.5) * 60, 1)


SEED_RATINGS: dict[str, float] = {
    **{n: round(seed_from_rank(r), 1) for n, _, r, _ in TT_MEN},
    **{n: round(seed_from_rank(r), 1) for n, _, r, _ in TT_WOMEN},
    **{n: _league_seed(n, rt) for n, _, _, rt in TT_LEAGUE},
}


class TTElo:
    def __init__(self, ratings: dict | None = None, counts: dict | None = None):
        self.ratings: dict[str, float] = dict(SEED_RATINGS)
        self.ratings.update(ratings or {})
        self.counts: dict[str, int] = counts or {}
        self._index = NameIndex(self.ratings.keys())

    @classmethod
    def load(cls, path: Path | str = STATE_PATH) -> "TTElo":
        p = Path(path)
        if p.exists():
            d = json.loads(p.read_text())
            return cls(d.get("ratings"), d.get("counts"))
        return cls()

    def save(self, path: Path | str = STATE_PATH) -> None:
        Path(path).write_text(json.dumps({"ratings": self.ratings, "counts": self.counts}))

    def rating(self, name: str, rank: int | None = None) -> tuple[float, bool]:
        key = name if name in self.ratings else self._index.find(name)
        if key:
            return self.ratings[key], True
        return (seed_from_rank(rank) if rank else DEFAULT_RATING), False

    def predict(self, a: str, b: str, rank_a: int | None = None, rank_b: int | None = None, best_of: int = 5) -> dict:
        ra, ka = self.rating(a, rank_a)
        rb, kb = self.rating(b, rank_b)
        # longer matches favour the stronger player slightly
        scale = 400.0 if best_of <= 5 else 370.0
        p = 1.0 / (1.0 + 10 ** ((rb - ra) / scale))
        return {"prob_a": p, "elo_a": round(ra, 1), "elo_b": round(rb, 1), "known_a": ka, "known_b": kb}

    def update(self, winner: str, loser: str) -> None:
        rw, _ = self.rating(winner)
        rl, _ = self.rating(loser)
        e = expected(rw, rl)
        for name, sign in ((winner, 1), (loser, -1)):
            n = self.counts.get(name, 0)
            k = K_BASE * (1.5 if n < 10 else 1.0)
            key = name if name in self.ratings else (self._index.find(name) or name)
            self.ratings[key] = (rw if sign == 1 else rl) + sign * k * (1 - e)
            self.counts[key] = n + 1
            self._index.add(key)


_tt: TTElo | None = None


def get_tt_elo() -> TTElo:
    global _tt
    if _tt is None:
        _tt = TTElo.load()
    return _tt

"""DemoProvider: a point-level match simulator used when no API key is configured.

Everything it produces is SIMULATED and tagged "source": "demo". Players are real
tour athletes (plus fictional league rosters), but scores, odds and results are
invented.

How the hidden "truth" is built (be aware when reading demo numbers):
  * Without an anchor, the true pre-match probability comes from the catalogue
    ratings in players.py (+ surface + day form).
  * The engine passes an `anchor` (the model's own pre-match estimate). The true
    probability is then that estimate + Gaussian noise (sd 0.08 in logit) - i.e.
    the demo ASSUMES a reasonably good model. The simulated bookmaker prices the
    true in-play probability with a 5-7 % margin plus its own smaller pricing error.
    The demo therefore demonstrates the pipeline (ingest -> model -> value ->
    staking -> CLV), NOT the real-world skill of the model.
Points are then played from the true serve-point probabilities.
"""
from __future__ import annotations

import itertools
import math
import random
from datetime import datetime, timedelta, timezone

from ..models import monte_carlo as mc
from ..players import TENNIS_TOURNAMENTS, TT_LEAGUE, TT_MEN, TT_TOURNAMENTS, TT_WOMEN, tennis_pool
from ..players import ATP_CHALLENGER, ATP_ITF, WTA_CHALLENGER, WTA_ITF  # noqa: F401
from .schema import make_match

BOOKMAKERS = ["Bet365", "Pinnacle", "Betfair Exchange", "Bwin", "Codere", "William Hill", "Sportium", "1xBet"]
TENNIS_POINTS = ["0", "15", "30", "40"]

LIVE_TARGET = {"tennis": {"ATP": 3, "WTA": 3, "Challenger": 2, "ITF": 2},
               "table_tennis": {"WTT": 2, "ITTF": 1, "Setka Cup": 2, "TT Elite Series": 2, "Czech Liga Pro": 1}}
UPCOMING_TARGET = {"tennis": {"ATP": 2, "WTA": 2, "Challenger": 2, "ITF": 1},
                   "table_tennis": {"WTT": 2, "ITTF": 1, "Setka Cup": 2, "TT Elite Series": 1, "Czech Liga Pro": 1}}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime) -> str:
    return d.isoformat(timespec="seconds").replace("+00:00", "Z")


def _expected(ra: float, rb: float, scale: float = 400.0) -> float:
    return 1.0 / (1.0 + 10 ** ((rb - ra) / scale))


class SimMatch:
    def __init__(self, rng: random.Random, mid: str, sport: str, category: str, tournament: str, surface,
                 best_of: int, a: dict, b: dict, start: datetime):
        self.rng = rng
        self.id, self.sport, self.category, self.tournament = mid, sport, category, tournament
        self.surface, self.best_of, self.a, self.b, self.start = surface, best_of, a, b, start
        self.status = "upcoming"
        self.winner = None
        self.finished_at: datetime | None = None
        self.bookmaker = rng.choice(BOOKMAKERS)
        self.margin = rng.uniform(0.05, 0.07)
        self.book_bias = rng.gauss(0, 0.045)  # persistent pricing error (logit)
        self.book_noise = 0.0
        # hidden truth
        if sport == "tennis":
            adj = lambda p: p.get("clay", 0) if surface == "clay" else p.get("grass", 0) if surface == "grass" else 0  # noqa: E731
            ra = a["rating"] + adj(a) + rng.gauss(0, 30)
            rb = b["rating"] + adj(b) + rng.gauss(0, 30)
            self.true_p = _expected(ra, rb, 340 if best_of == 5 else 400)
            self.pa, self.pb = mc.serve_probs_for(self.true_p, "tennis", best_of, a.get("tour"))
        else:
            ra, rb = a["rating"] + rng.gauss(0, 35), b["rating"] + rng.gauss(0, 35)
            self.true_p = _expected(ra, rb)
            self.pa, self.pb = mc.serve_probs_for(self.true_p, "table_tennis", best_of)
        self.pre_true_p = self.true_p
        # score state
        self.sets: list[list[int]] = []  # completed sets / games
        self.games = [0, 0]  # tennis: current set games
        self.points = [0, 0]
        self.won = [0, 0]  # sets (tennis) or games (TT) won
        self.server = rng.randint(0, 1)
        self.game_first = self.server  # TT: first server of current game / tennis: tb first server
        self.tiebreak = False
        self.stats = {"aces": [0, 0], "double_faults": [0, 0], "service_points": [0, 0],
                      "service_points_won": [0, 0], "breaks": [0, 0], "points_won": [0, 0]}
        self.closing_odds = None

    def set_truth(self, p: float) -> None:
        self.true_p = self.pre_true_p = min(0.97, max(0.03, p))
        self.pa, self.pb = mc.serve_probs_for(self.true_p, self.sport, self.best_of, self.a.get("tour"))

    # ------------------------------------------------------------- simulation
    def _current_server(self) -> int:
        k = self.points[0] + self.points[1]
        if self.sport == "table_tennis":
            return mc._tt_server(k, self.game_first)
        if self.tiebreak:
            return mc._tb_server(k, self.game_first)
        return self.server

    def play_point(self) -> None:
        if self.status != "live":
            return
        s = self._current_server()
        p = self.pa if s == 0 else self.pb
        server_wins = self.rng.random() < p
        w = s if server_wins else 1 - s
        st = self.stats
        st["service_points"][s] += 1
        st["points_won"][w] += 1
        if server_wins:
            st["service_points_won"][s] += 1
            if self.sport == "tennis" and self.rng.random() < (0.13 if self.a.get("tour") == "ATP" else 0.06):
                st["aces"][s] += 1
        elif self.sport == "tennis" and self.rng.random() < 0.09:
            st["double_faults"][s] += 1
        self.points[w] += 1
        if self.sport == "table_tennis":
            self._tt_after_point()
        else:
            self._tennis_after_point(s, w)

    def _tt_after_point(self) -> None:
        a, b = self.points
        if (a >= 11 or b >= 11) and abs(a - b) >= 2:
            w = 0 if a > b else 1
            self.sets.append([a, b])
            self.won[w] += 1
            self.points = [0, 0]
            self.game_first = 1 - self.game_first
            if self.won[w] >= self.best_of // 2 + 1:
                self._finish(w)

    def _tennis_after_point(self, s: int, w: int) -> None:
        a, b = self.points
        if self.tiebreak:
            if (a >= 7 or b >= 7) and abs(a - b) >= 2:
                self.games[w] += 1
                self.server = 1 - self.game_first
                self._end_set(w)
            return
        if (a >= 4 or b >= 4) and abs(a - b) >= 2:
            if w != s:
                self.stats["breaks"][w] += 1
            self.games[w] += 1
            self.points = [0, 0]
            self.server = 1 - self.server
            ga, gb = self.games
            if (ga >= 6 or gb >= 6) and abs(ga - gb) >= 2 or ga == 7 or gb == 7:
                self._end_set(0 if ga > gb else 1)
            elif ga == 6 and gb == 6:
                self.tiebreak = True
                self.game_first = self.server

    def _end_set(self, w: int) -> None:
        self.sets.append(list(self.games))
        self.won[w] += 1
        self.games = [0, 0]
        self.points = [0, 0]
        self.tiebreak = False
        if self.won[w] >= self.best_of // 2 + 1:
            self._finish(w)

    def _finish(self, w: int) -> None:
        self.status = "finished"
        self.winner = "a" if w == 0 else "b"
        self.finished_at = _now()

    def fast_forward(self, n_points: int) -> None:
        for _ in range(n_points):
            if self.status != "live":
                break
            self.play_point()

    # ------------------------------------------------------------- pricing
    def state(self) -> mc.MatchState:
        if self.sport == "table_tennis":
            return mc.MatchState("table_tennis", self.best_of, tuple(self.won), (0, 0), tuple(self.points),
                                 self._current_server())
        return mc.MatchState("tennis", self.best_of, tuple(self.won), tuple(self.games), tuple(self.points),
                             self._current_server(), self.tiebreak)

    def true_prob_now(self) -> float:
        if self.status == "finished":
            return 1.0 if self.winner == "a" else 0.0
        if self.status == "upcoming":
            return mc.prematch_prob_exact(self.pa, self.pb, self.sport, self.best_of)
        return mc.inplay_prob_exact(self.pa, self.pb, self.state())

    def odds(self) -> dict | None:
        if self.status == "finished":
            return None
        p = min(max(self.true_prob_now(), 0.005), 0.995)
        self.book_noise = 0.85 * self.book_noise + self.rng.gauss(0, 0.015)
        x = math.log(p / (1 - p)) + self.book_bias + self.book_noise
        q = 1 / (1 + math.exp(-x))
        oa = 1 / (q * (1 + self.margin))
        ob = 1 / ((1 - q) * (1 + self.margin))
        clamp = lambda o: round(min(max(o, 1.01), 41.0), 2)  # noqa: E731
        oa, ob = clamp(oa), clamp(ob)
        if oa <= 1.01 or ob <= 1.01:  # market effectively closed
            return None
        return {"player_a": oa, "player_b": ob}

    # ------------------------------------------------------------- export
    def score(self) -> dict:
        if self.sport == "table_tennis":
            sets = [list(s) for s in self.sets] + ([list(self.points)] if self.status == "live" else [])
            return {"sets": sets, "games": list(self.won),
                    "points": f"{self.points[0]}-{self.points[1]}" if self.status == "live" else None}
        sets = [list(s) for s in self.sets] + ([list(self.games)] if self.status == "live" else [])
        if self.status != "live":
            pts = None
        elif self.tiebreak:
            pts = f"{self.points[0]}-{self.points[1]}"
        else:
            a, b = self.points
            if a >= 3 and b >= 3:
                pts = "40-40" if a == b else ("AD-40" if a > b else "40-AD")
            else:
                pts = f"{TENNIS_POINTS[min(a, 3)]}-{TENNIS_POINTS[min(b, 3)]}"
        return {"sets": sets, "games": list(self.games) if self.status == "live" else [0, 0], "points": pts,
                "tiebreak": self.tiebreak, "sets_won": list(self.won)}

    def to_common(self) -> dict:
        srv = self._current_server() if self.status == "live" else None
        stats = {k: list(v) for k, v in self.stats.items()}
        if self.sport == "table_tennis":
            stats = {"points_won": stats["points_won"], "service_points": stats["service_points"],
                     "service_points_won": stats["service_points_won"]}
        m = make_match(self.sport, self.id, self.a["name"], self.b["name"], self.tournament, self.surface,
                       self.status, self.score(), self.odds(), source="demo", category=self.category,
                       start_time=_iso(self.start), best_of=self.best_of,
                       rank_a=self.a.get("rank") or None, rank_b=self.b.get("rank") or None,
                       country_a=self.a.get("country"), country_b=self.b.get("country"), bookmaker=self.bookmaker,
                       stats=stats, winner=self.winner, form_a=self.a.get("form"), form_b=self.b.get("form"))
        m["server"] = None if srv is None else ("a" if srv == 0 else "b")
        return m


class DemoProvider:
    name = "demo"
    sports = ("tennis", "table_tennis")
    provides_odds = True
    provides_scores = True

    def __init__(self, seed: int | None = None, points_per_tick: float = 1.0, finished_keep_minutes: float = 8.0,
                 anchor=None, model_noise: float = 0.08):
        self.rng = random.Random(seed)
        self.anchor = anchor
        self.model_noise = model_noise
        self.matches: dict[str, SimMatch] = {}
        self.counter = itertools.count(1)
        self.points_per_tick = points_per_tick
        self.finished_keep = timedelta(minutes=finished_keep_minutes)
        self.status = "ok"
        self.last_count = 0
        self.enabled = True
        self._form: dict[str, list[str]] = {}
        self._populate(initial=True)

    # ------------------------------------------------------------- roster
    def _busy(self) -> set[str]:
        return {p for m in self.matches.values() if m.status != "finished" for p in (m.a["name"], m.b["name"])}

    def _pick_pair(self, pool: list[dict]) -> tuple[dict, dict] | None:
        busy = self._busy()
        free = [p for p in pool if p["name"] not in busy]
        if len(free) < 2:
            return None
        a = self.rng.choice(free)
        # pair with someone of comparable level most of the time
        free.remove(a)
        free.sort(key=lambda p: abs(p["rating"] - a["rating"]))
        b = self.rng.choice(free[: max(3, len(free) // 3)])
        return (a, b) if self.rng.random() < 0.5 else (b, a)

    def _form_for(self, name: str, rating: float) -> list[str]:
        if name not in self._form:
            p = min(0.85, max(0.25, 0.5 + (rating - 1800) / 900))
            self._form[name] = ["W" if self.rng.random() < p else "L" for _ in range(10)]
        return self._form[name]

    def _tennis_pool(self, category: str, tournament: str) -> list[dict]:
        if category in ("ATP", "WTA"):
            raw, tour = tennis_pool(category), category
        else:
            women = tournament.startswith("WTA") or " W" in tournament
            tour = "WTA" if women else "ATP"
            raw = (WTA_CHALLENGER if women else ATP_CHALLENGER) if category == "Challenger" else \
                (WTA_ITF if women else ATP_ITF)
        return [{"name": n, "country": c, "rank": r, "rating": rt, "clay": cl, "grass": gr, "tour": tour,
                 "form": self._form_for(n, rt)} for n, c, r, rt, cl, gr in raw]

    def _tt_pool(self, category: str) -> list[dict]:
        if category in ("Setka Cup", "TT Elite Series", "Czech Liga Pro"):
            raw = TT_LEAGUE
        else:
            raw = TT_MEN if self.rng.random() < 0.6 else TT_WOMEN
        return [{"name": n, "country": c, "rank": r or None, "rating": rt, "form": self._form_for(n, rt)}
                for n, c, r, rt in raw]

    def _new_match(self, sport: str, category: str, start: datetime) -> SimMatch | None:
        n = next(self.counter)
        if sport == "tennis":
            tname, surface, _ = self.rng.choice(TENNIS_TOURNAMENTS[category])
            pair = self._pick_pair(self._tennis_pool(category, tname))
            if not pair:
                return None
            sim = SimMatch(self.rng, f"demo-ten-{n:04d}", "tennis", category, tname, surface, 3, *pair, start)
        else:
            tname, bo = self.rng.choice(TT_TOURNAMENTS[category])
            pair = self._pick_pair(self._tt_pool(category))
            if not pair:
                return None
            sim = SimMatch(self.rng, f"demo-tt-{n:04d}", "table_tennis", category, tname, None, bo, *pair, start)
        if self.anchor is not None:
            try:
                p = float(self.anchor(sim.to_common()))
                x = math.log(p / (1 - p)) + self.rng.gauss(0, self.model_noise)
                sim.set_truth(1 / (1 + math.exp(-x)))
            except Exception:  # noqa: BLE001 - fall back to catalogue-based truth
                pass
        return sim

    def _populate(self, initial: bool = False) -> None:
        now = _now()
        for sport in ("tennis", "table_tennis"):
            for cat, target in LIVE_TARGET[sport].items():
                live = [m for m in self.matches.values() if m.sport == sport and m.category == cat and m.status == "live"]
                if initial:
                    for _ in range(target - len(live)):
                        m = self._new_match(sport, cat, now - timedelta(minutes=self.rng.uniform(5, 80)))
                        if m:
                            m.status = "live"
                            m.closing_odds = m.odds()
                            m.fast_forward(self.rng.randint(0, 110 if sport == "tennis" else 45))
                            self.matches[m.id] = m
                elif len(live) < target:
                    # keep the board lively: the next scheduled match of this category starts now
                    nxt = sorted((m for m in self.matches.values() if m.sport == sport and m.category == cat
                                  and m.status == "upcoming"), key=lambda m: m.start)
                    for m in nxt[: target - len(live)]:
                        m.start = min(m.start, now)
                        m.closing_odds = m.odds()
                        m.status = "live"
                up = [m for m in self.matches.values() if m.sport == sport and m.category == cat and m.status == "upcoming"]
                for _ in range(UPCOMING_TARGET[sport][cat] - len(up)):
                    lo, hi = (1.5, 25) if initial else (6, 40)
                    m = self._new_match(sport, cat, now + timedelta(minutes=self.rng.uniform(lo, hi)))
                    if m:
                        self.matches[m.id] = m

    # ------------------------------------------------------------- tick
    def step(self) -> None:
        now = _now()
        for m in list(self.matches.values()):
            if m.status == "upcoming" and m.start <= now:
                m.closing_odds = m.odds()
                m.status = "live"
            elif m.status == "live":
                n = 1 if self.rng.random() < self.points_per_tick else 0
                if m.sport == "table_tennis" and self.rng.random() < 0.35:
                    n += 1
                m.fast_forward(n)
                if m.status == "finished":
                    for p, res in ((m.a["name"], m.winner == "a"), (m.b["name"], m.winner == "b")):
                        f = self._form.setdefault(p, [])
                        f.append("W" if res else "L")
                        del f[:-10]
            elif m.status == "finished" and m.finished_at and now - m.finished_at > self.finished_keep:
                del self.matches[m.id]
        fin = sorted((m for m in self.matches.values() if m.status == "finished"), key=lambda m: m.finished_at)
        for m in fin[:-12]:
            del self.matches[m.id]
        self._populate()

    def fetch(self) -> list[dict]:
        self.step()
        out = [m.to_common() for m in self.matches.values()]
        self.last_count = len(out)
        return out

    def info(self) -> dict:
        return {"name": "demo", "enabled": True, "status": "ok", "sports": list(self.sports), "matches": self.last_count,
                "note": "Simulated data (no API keys configured)"}

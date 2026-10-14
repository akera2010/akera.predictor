"""Point-level Markov model + vectorised Monte Carlo for tennis and table tennis.

Inputs are *point-win probabilities on serve*:
    pa = P(A wins a point when A serves), pb = P(B wins a point when B serves).
Points are i.i.d. given the server (classic Barnett/Clarke assumption). From those
we compute exactly (dynamic programming) the probability of winning a game,
tie-break, set and match from ANY in-play score, and we also run a numpy
vectorised Monte Carlo (default 10,000 iterations) that samples each remaining
game/tie-break from its exact point-level win probability. The simulation is
therefore distributionally identical to a point-by-point simulation but ~10x
faster, and additionally yields the final set-score distribution.

Simplifications (documented on purpose): every set (including the decider) uses a
standard 7-point tie-break at 6-6; no momentum / fatigue effects.

Servers are encoded as 0 = player A, 1 = player B.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

DEFAULT_ITERATIONS = 10_000
TOUR_SERVE_BASE = {"ATP": 0.64, "WTA": 0.565, "default": 0.62}
TT_SERVE_BASE = 0.53


def _r(x: float) -> float:
    return round(float(min(max(x, 0.01), 0.99)), 4)


# --------------------------------------------------------------------- tennis
@lru_cache(maxsize=100_000)
def game_prob(p: float, a: int = 0, b: int = 0) -> float:
    """P(server wins the game) when the server has a points and receiver b points."""
    if a >= 4 and a - b >= 2:
        return 1.0
    if b >= 4 and b - a >= 2:
        return 0.0
    if a >= 3 and b >= 3:
        d = p * p / (p * p + (1 - p) * (1 - p))
        if a == b:
            return d
        return p + (1 - p) * d if a > b else p * d
    return p * game_prob(p, a + 1, b) + (1 - p) * game_prob(p, a, b + 1)


def _tb_server(k: int, first: int) -> int:
    if k == 0:
        return first
    return first if ((k - 1) // 2) % 2 == 1 else 1 - first


def tb_first_from_server(k: int, server: int) -> int:
    if k == 0:
        return server
    return server if ((k - 1) // 2) % 2 == 1 else 1 - server


@lru_cache(maxsize=200_000)
def tb_prob(pa: float, pb: float, i: int = 0, j: int = 0, first: int = 0, to: int = 7) -> float:
    """P(A wins tie-break) from points i (A) - j (B); `first` served point 0."""
    if i >= to and i - j >= 2:
        return 1.0
    if j >= to and j - i >= 2:
        return 0.0
    if i >= to - 1 and j >= to - 1 and i == j:
        pw, pl = pa * (1 - pb), (1 - pa) * pb
        return pw / (pw + pl)
    s = _tb_server(i + j, first)
    p = pa if s == 0 else 1 - pb
    return p * tb_prob(pa, pb, i + 1, j, first, to) + (1 - p) * tb_prob(pa, pb, i, j + 1, first, to)


def _set_over(ga: int, gb: int) -> int:
    """0 = not over, 1 = A won set, 2 = B won set."""
    if (ga >= 6 and ga - gb >= 2) or ga == 7:
        return 1
    if (gb >= 6 and gb - ga >= 2) or gb == 7:
        return 2
    return 0


@lru_cache(maxsize=200_000)
def set_outcomes(pa: float, pb: float, ga: int = 0, gb: int = 0, srv: int = 0) -> tuple:
    """Probabilities (A wins & next-set first server A, A wins & B, B wins & A, B wins & B).
    `srv` = server of the next game in this set."""
    over = _set_over(ga, gb)
    if over:
        out = [0.0, 0.0, 0.0, 0.0]
        out[(0 if over == 1 else 2) + srv] = 1.0
        return tuple(out)
    if ga == 6 and gb == 6:
        pt = tb_prob(pa, pb, 0, 0, srv)
        nxt = 1 - srv
        out = [0.0, 0.0, 0.0, 0.0]
        out[nxt] += pt
        out[2 + nxt] += 1 - pt
        return tuple(out)
    g = game_prob(pa) if srv == 0 else 1 - game_prob(pb)
    w = set_outcomes(pa, pb, ga + 1, gb, 1 - srv)
    l = set_outcomes(pa, pb, ga, gb + 1, 1 - srv)
    return tuple(g * x + (1 - g) * y for x, y in zip(w, l))


@lru_cache(maxsize=100_000)
def tennis_match_prob(pa: float, pb: float, sa: int = 0, sb: int = 0, srv: int = 0, best_of: int = 3) -> float:
    need = best_of // 2 + 1
    if sa >= need:
        return 1.0
    if sb >= need:
        return 0.0
    o = set_outcomes(pa, pb, 0, 0, srv)
    return (o[0] * tennis_match_prob(pa, pb, sa + 1, sb, 0, best_of)
            + o[1] * tennis_match_prob(pa, pb, sa + 1, sb, 1, best_of)
            + o[2] * tennis_match_prob(pa, pb, sa, sb + 1, 0, best_of)
            + o[3] * tennis_match_prob(pa, pb, sa, sb + 1, 1, best_of))


# --------------------------------------------------------------- table tennis
def _tt_server(k: int, first: int) -> int:
    if k < 20:
        return first if (k // 2) % 2 == 0 else 1 - first
    return first if k % 2 == 0 else 1 - first


def tt_first_from_server(k: int, server: int) -> int:
    if k < 20:
        return server if (k // 2) % 2 == 0 else 1 - server
    return server if k % 2 == 0 else 1 - server


@lru_cache(maxsize=200_000)
def tt_game_prob(pa: float, pb: float, i: int = 0, j: int = 0, first: int = 0, to: int = 11) -> float:
    if i >= to and i - j >= 2:
        return 1.0
    if j >= to and j - i >= 2:
        return 0.0
    if i >= to - 1 and j >= to - 1 and i == j:
        pw, pl = pa * (1 - pb), (1 - pa) * pb
        return pw / (pw + pl)
    s = _tt_server(i + j, first)
    p = pa if s == 0 else 1 - pb
    return p * tt_game_prob(pa, pb, i + 1, j, first, to) + (1 - p) * tt_game_prob(pa, pb, i, j + 1, first, to)


@lru_cache(maxsize=100_000)
def tt_match_prob(pa: float, pb: float, ga: int = 0, gb: int = 0, first: int = 0, best_of: int = 5) -> float:
    need = best_of // 2 + 1
    if ga >= need:
        return 1.0
    if gb >= need:
        return 0.0
    g = tt_game_prob(pa, pb, 0, 0, first)
    return g * tt_match_prob(pa, pb, ga + 1, gb, 1 - first, best_of) + (1 - g) * tt_match_prob(pa, pb, ga, gb + 1, 1 - first, best_of)


# ------------------------------------------------------------- match state
@dataclass
class MatchState:
    """Normalised in-play state. For tennis: sets_won / games (current set) / points
    (current game or tie-break). For table tennis: sets_won holds GAMES won and
    points the current game's points; `games` is unused."""
    sport: str = "tennis"
    best_of: int = 3
    sets_won: tuple = (0, 0)
    games: tuple = (0, 0)
    points: tuple = (0, 0)
    server: int | None = None  # who serves the NEXT point (0=A,1=B), None unknown
    tiebreak: bool = False
    set_scores: list = field(default_factory=list)  # completed set/game scores [(a,b),...]


POINT_MAP = {"0": 0, "15": 1, "30": 2, "40": 3, "A": 4, "AD": 4, "Ad": 4}


def parse_points(points: str | None, tennis: bool, tiebreak: bool = False) -> tuple[int, int]:
    if not points or "-" not in str(points):
        return (0, 0)
    a, b = [x.strip() for x in str(points).split("-", 1)]
    if tennis and not tiebreak:
        pa, pb = POINT_MAP.get(a, None), POINT_MAP.get(b, None)
        if pa is None or pb is None:
            try:
                return (int(a), int(b))
            except ValueError:
                return (0, 0)
        if pa == 4:
            pb = 3
        if pb == 4:
            pa = 3
        return (pa, pb)
    try:
        return (int(a), int(b))
    except ValueError:
        return (0, 0)


def state_from_score(sport: str, score: dict | None, server: str | None, best_of: int, status: str) -> MatchState:
    score = score or {}
    srv = {"a": 0, "b": 1}.get(server or "", None)
    sets = [tuple(s) for s in (score.get("sets") or []) if isinstance(s, (list, tuple)) and len(s) == 2]
    if sport == "table_tennis":
        done, cur = [], (0, 0)
        for s in sets:
            a, b = s
            if (a >= 11 or b >= 11) and abs(a - b) >= 2:
                done.append(s)
            else:
                cur = s
        ga = sum(1 for a, b in done if a > b)
        gb = len(done) - ga
        pts = parse_points(score.get("points"), tennis=False) if score.get("points") else cur
        return MatchState("table_tennis", best_of, (ga, gb), (0, 0), pts, srv, False, done)
    done, cur = [], (0, 0)
    for s in sets:
        a, b = s
        if _set_over(a, b):
            done.append(s)
        else:
            cur = s
    if score.get("games") and len(score["games"]) == 2 and not cur and status == "live":
        cur = tuple(score["games"])
    sa = sum(1 for a, b in done if a > b)
    sb = len(done) - sa
    tiebreak = bool(score.get("tiebreak")) or cur == (6, 6)
    pts = parse_points(score.get("points"), tennis=True, tiebreak=tiebreak)
    return MatchState("tennis", best_of, (sa, sb), tuple(cur), pts, srv, tiebreak, done)


# ----------------------------------------------------------- exact in-play
def _tennis_inplay_exact_srv(pa, pb, st: MatchState, srv: int) -> float:
    ga, gb = st.games
    i, j = st.points
    sa, sb = st.sets_won
    if st.tiebreak:
        first = tb_first_from_server(i + j, srv)
        pt = tb_prob(pa, pb, i, j, first)
        nxt = 1 - first
        o = (pt if nxt == 0 else 0.0, pt if nxt == 1 else 0.0,
             (1 - pt) if nxt == 0 else 0.0, (1 - pt) if nxt == 1 else 0.0)
    elif (i, j) == (0, 0):
        o = set_outcomes(pa, pb, ga, gb, srv)
    else:
        g = game_prob(pa, i, j) if srv == 0 else 1 - game_prob(pb, j, i)
        w = set_outcomes(pa, pb, ga + 1, gb, 1 - srv)
        l = set_outcomes(pa, pb, ga, gb + 1, 1 - srv)
        o = tuple(g * x + (1 - g) * y for x, y in zip(w, l))
    bo = st.best_of
    return (o[0] * tennis_match_prob(pa, pb, sa + 1, sb, 0, bo) + o[1] * tennis_match_prob(pa, pb, sa + 1, sb, 1, bo)
            + o[2] * tennis_match_prob(pa, pb, sa, sb + 1, 0, bo) + o[3] * tennis_match_prob(pa, pb, sa, sb + 1, 1, bo))


def _tt_inplay_exact_srv(pa, pb, st: MatchState, srv: int) -> float:
    ga, gb = st.sets_won
    i, j = st.points
    first = tt_first_from_server(i + j, srv)
    g = tt_game_prob(pa, pb, i, j, first)
    nxt = 1 - first
    return g * tt_match_prob(pa, pb, ga + 1, gb, nxt, st.best_of) + (1 - g) * tt_match_prob(pa, pb, ga, gb + 1, nxt, st.best_of)


def inplay_prob_exact(pa: float, pb: float, st: MatchState) -> float:
    """Exact P(A wins match) from the current state (averaging over the server if unknown)."""
    pa, pb = _r(pa), _r(pb)
    fn = _tt_inplay_exact_srv if st.sport == "table_tennis" else _tennis_inplay_exact_srv
    if st.sport == "tennis" and _set_over(*st.games):
        st = MatchState(st.sport, st.best_of, (st.sets_won[0] + (st.games[0] > st.games[1]),
                                               st.sets_won[1] + (st.games[1] > st.games[0])), (0, 0), (0, 0), st.server)
    if st.server is None:
        return 0.5 * (fn(pa, pb, st, 0) + fn(pa, pb, st, 1))
    return fn(pa, pb, st, st.server)


def prematch_prob_exact(pa: float, pb: float, sport: str, best_of: int) -> float:
    pa, pb = _r(pa), _r(pb)
    if sport == "table_tennis":
        return 0.5 * (tt_match_prob(pa, pb, 0, 0, 0, best_of) + tt_match_prob(pa, pb, 0, 0, 1, best_of))
    return 0.5 * (tennis_match_prob(pa, pb, 0, 0, 0, best_of) + tennis_match_prob(pa, pb, 0, 0, 1, best_of))


# ------------------------------------------------------------ Monte Carlo
def simulate(pa: float, pb: float, st: MatchState | None = None, sport: str = "tennis", best_of: int = 3,
             iterations: int = DEFAULT_ITERATIONS, seed: int | None = None) -> dict:
    """Vectorised Monte Carlo from the current state. Returns prob_a, iterations and
    the distribution of final set (tennis) / game (table tennis) scores."""
    pa, pb = _r(pa), _r(pb)
    if st is None:
        st = MatchState(sport, best_of)
    rng = np.random.default_rng(seed)
    n = int(iterations)
    need = st.best_of // 2 + 1
    sa = np.full(n, st.sets_won[0], dtype=np.int16)
    sb = np.full(n, st.sets_won[1], dtype=np.int16)
    if st.server is None:
        srv0 = rng.integers(0, 2, n).astype(np.int8)
    else:
        srv0 = np.full(n, st.server, dtype=np.int8)

    if st.sport == "table_tennis":
        i, j = st.points
        k = i + j
        first_cur = np.where(srv0 == 0, tt_first_from_server(k, 0), tt_first_from_server(k, 1)).astype(np.int8)
        g_cur = np.where(first_cur == 0, tt_game_prob(pa, pb, i, j, 0), tt_game_prob(pa, pb, i, j, 1))
        win = rng.random(n) < g_cur
        sa += win
        sb += ~win
        first = (1 - first_cur).astype(np.int8)
        G = np.array([tt_game_prob(pa, pb, 0, 0, 0), tt_game_prob(pa, pb, 0, 0, 1)])
        active = (sa < need) & (sb < need)
        while active.any():
            win = rng.random(n) < G[first]
            sa += (win & active)
            sb += (~win & active)
            first = (1 - first).astype(np.int8)
            active = (sa < need) & (sb < need)
    else:
        ga = np.full(n, st.games[0], dtype=np.int16)
        gb = np.full(n, st.games[1], dtype=np.int16)
        srv = srv0.copy()
        i, j = st.points
        gA, gB = game_prob(pa), game_prob(pb)
        TB = np.array([tb_prob(pa, pb, 0, 0, 0), tb_prob(pa, pb, 0, 0, 1)])

        def close_sets(active):
            nonlocal sa, sb, ga, gb
            a_set = active & (((ga >= 6) & (ga - gb >= 2)) | (ga == 7))
            b_set = active & (((gb >= 6) & (gb - ga >= 2)) | (gb == 7))
            sa = sa + a_set
            sb = sb + b_set
            ended = a_set | b_set
            ga = np.where(ended, 0, ga)
            gb = np.where(ended, 0, gb)

        everyone = np.ones(n, dtype=bool)
        # current game / tie-break in progress
        if st.tiebreak:
            k = i + j
            first = np.where(srv == 0, tb_first_from_server(k, 0), tb_first_from_server(k, 1))
            p_cur = np.where(first == 0, tb_prob(pa, pb, i, j, 0), tb_prob(pa, pb, i, j, 1))
            win = rng.random(n) < p_cur
            ga = ga + win
            gb = gb + ~win
            srv = (1 - first).astype(np.int8)
            close_sets(everyone)
        elif (i, j) != (0, 0):
            p_cur = np.where(srv == 0, game_prob(pa, i, j), 1 - game_prob(pb, j, i))
            win = rng.random(n) < p_cur
            ga = ga + win
            gb = gb + ~win
            srv = (1 - srv).astype(np.int8)
            close_sets(everyone)
        else:
            close_sets(everyone)
        active = (sa < need) & (sb < need)
        while active.any():
            in_tb = active & (ga == 6) & (gb == 6)
            p = np.where(srv == 0, gA, 1 - gB)
            p = np.where(in_tb, TB[srv], p)
            win = rng.random(n) < p
            ga = ga + (win & active)
            gb = gb + (~win & active)
            srv = np.where(active, 1 - srv, srv).astype(np.int8)
            close_sets(active)
            active = (sa < need) & (sb < need)
    a_won = sa >= need
    keys, counts = np.unique(np.stack([sa, sb], axis=1), axis=0, return_counts=True)
    dist = {f"{int(a)}-{int(b)}": round(float(c) / n, 4) for (a, b), c in zip(keys, counts)}
    dist = dict(sorted(dist.items(), key=lambda kv: (-int(kv[0].split('-')[0]), kv[0])))
    return {"prob_a": float(a_won.mean()), "iterations": n, "set_score_dist": dist}


# ----------------------------------------------------- calibration helpers
def serve_base(sport: str, tour: str | None = None) -> float:
    if sport == "table_tennis":
        return TT_SERVE_BASE
    return TOUR_SERVE_BASE.get(tour or "default", TOUR_SERVE_BASE["default"])


@lru_cache(maxsize=50_000)
def _fit_delta(target: float, sport: str, best_of: int, base: float) -> float:
    lo, hi = -0.3, 0.3
    for _ in range(40):
        mid = (lo + hi) / 2
        p = prematch_prob_exact(base + mid, base - mid, sport, best_of)
        if p < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def serve_probs_for(target_prob: float, sport: str, best_of: int, tour: str | None = None) -> tuple[float, float]:
    """Find symmetric serve-point probabilities (base+d, base-d) whose pre-match
    match-win probability equals `target_prob`."""
    base = serve_base(sport, tour)
    t = round(min(max(target_prob, 0.005), 0.995), 3)
    d = _fit_delta(t, sport, best_of, base)
    return _r(base + d), _r(base - d)

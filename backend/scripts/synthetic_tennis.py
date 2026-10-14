"""SYNTHETIC tennis match generator (fallback only).

Used by train_models.py when the Jeff Sackmann CSVs cannot be downloaded (e.g. no
network access to raw.githubusercontent.com). It writes CSVs in the same column
layout as tennis_atp / tennis_wta so the exact same training pipeline runs.

The generated world is a *simulation*: players have a latent skill (Elo-like scale,
seeded from akeraten.players for real names plus anonymous filler players), skill
drifts over the years, surface preferences, and matches are drawn from a
logistic model; tournaments are knock-out draws with a rolling 52-week ranking.
Metrics obtained on this data say nothing about real-world accuracy.
"""
from __future__ import annotations

import csv
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from akeraten.models.monte_carlo import serve_probs_for  # noqa: E402
from akeraten.players import (ATP, ATP_CHALLENGER, ATP_ITF, WTA, WTA_CHALLENGER,  # noqa: E402
                              WTA_ITF)

COLUMNS = ["tourney_id", "tourney_name", "surface", "draw_size", "tourney_level", "tourney_date", "match_num",
           "winner_name", "winner_ioc", "loser_name", "loser_ioc", "score", "best_of", "round",
           "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon", "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon",
           "winner_rank", "winner_rank_points", "loser_rank", "loser_rank_points"]

ROUND_NAMES = {128: "R128", 64: "R64", 32: "R32", 16: "R16", 8: "QF", 4: "SF", 2: "F"}
POINTS = {"G": 2000, "M": 1000, "A": 250}
SLAM_WEEKS = {3: ("Australian Open", "Hard"), 21: ("Roland Garros", "Clay"), 27: ("Wimbledon", "Grass"),
              35: ("US Open", "Hard")}
MASTERS_WEEKS = {10: "Hard", 12: "Hard", 15: "Clay", 18: "Clay", 19: "Clay", 31: "Hard", 33: "Hard", 41: "Hard",
                 44: "Hard"}


def surface_for_week(w: int) -> str:
    if 14 <= w <= 22:
        return "Clay"
    if 23 <= w <= 27:
        return "Grass"
    if 28 <= w <= 30:
        return "Clay"
    if w >= 40:
        return "Carpet" if w % 3 == 0 else "Hard"
    return "Hard"


def _players(tour: str, rng, n_total: int = 420):
    lists = (ATP, ATP_CHALLENGER, ATP_ITF) if tour == "atp" else (WTA, WTA_CHALLENGER, WTA_ITF)
    out = []
    for lst in lists:
        for name, cc, rank, rating, clay, grass in lst:
            out.append({"name": name, "ioc": cc, "skill": float(rating), "Clay": clay, "Grass": grass,
                        "slope": rng.normal(0, 18), "style": rng.normal(0, 0.015)})
    i = 0
    while len(out) < n_total:
        i += 1
        out.append({"name": f"Synthetic {tour.upper()} Player {i:03d}", "ioc": "SYN",
                    "skill": float(np.clip(rng.normal(1640, 105), 1380, 1960)),
                    "Clay": rng.normal(0, 35), "Grass": rng.normal(0, 35),
                    "slope": rng.normal(0, 18), "style": rng.normal(0, 0.015)})
    for p in out:
        p["Hard"] = 0.0
        p["Carpet"] = 10.0 if p["Grass"] > 0 else -5.0
    return out


def generate(out_dir: Path, years: range, seed: int = 7) -> list[Path]:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for tour in ("atp", "wta"):
        players = _players(tour, rng)
        n = len(players)
        last_year = years[-1]
        points_log: list[list[tuple[int, int]]] = [[] for _ in range(n)]
        order0 = np.argsort([-p["skill"] for p in players])
        rank = np.empty(n, dtype=int)
        rank[order0] = np.arange(1, n + 1)
        rank_pts = np.zeros(n, dtype=int)
        for year in years:
            yearly_noise = rng.normal(0, 22, n)
            skill = np.array([p["skill"] + p["slope"] * (year - last_year) for p in players]) + yearly_noise
            rows = []
            monday = date(year, 1, 1) + timedelta(days=(7 - date(year, 1, 1).weekday()) % 7)
            for week in range(1, 47):
                abs_week = year * 53 + week
                # rolling 52-week ranking
                if any(points_log):
                    totals = np.array([sum(pt for wk, pt in log if abs_week - wk <= 52) for log in points_log])
                    rank_pts = totals
                    order = np.lexsort((-skill, -totals))
                    rank[order] = np.arange(1, n + 1)
                tdate = monday + timedelta(weeks=week - 1)
                events = []
                if week in SLAM_WEEKS:
                    events.append((SLAM_WEEKS[week][0], SLAM_WEEKS[week][1], "G", 128))
                elif week in MASTERS_WEEKS:
                    events.append((f"Masters W{week}", MASTERS_WEEKS[week], "M", 64))
                else:
                    s = surface_for_week(week)
                    events += [(f"Tour 250 W{week}A", s, "A", 32), (f"Tour 250 W{week}B", s, "A", 32)]
                by_rank = np.argsort(rank)
                used = set()
                for ev_i, (tname, surf, level, draw) in enumerate(events):
                    if level == "G":
                        entrants = list(by_rank[:draw])
                    elif level == "M":
                        pool = list(by_rank[:draw + 16])
                        entrants = list(rng.choice(pool, draw, replace=False))
                    else:
                        pool = [i for i in by_rank[:170] if i not in used]
                        w = np.array([0.25 if rank[i] <= 10 else 1.0 for i in pool])
                        entrants = list(rng.choice(pool, draw, replace=False, p=w / w.sum()))
                        used.update(entrants)
                    rng.shuffle(entrants)
                    best_of = 5 if (level == "G" and tour == "atp") else 3
                    scale = 340.0 if best_of == 5 else 400.0
                    tid = f"{year}-{tour}-{week:02d}{ev_i}"
                    alive = entrants
                    match_num = 0
                    while len(alive) > 1:
                        rname = ROUND_NAMES.get(len(alive), "R")
                        nxt = []
                        for k in range(0, len(alive), 2):
                            a, b = alive[k], alive[k + 1]
                            ra = skill[a] + players[a][surf]
                            rb = skill[b] + players[b][surf]
                            p_a = 1 / (1 + 10 ** ((rb - ra) / scale))
                            a_wins = rng.random() < p_a
                            wi, li = (a, b) if a_wins else (b, a)
                            pw = p_a if a_wins else 1 - p_a
                            sw, sl = serve_probs_for(pw, "tennis", best_of, "ATP" if tour == "atp" else "WTA")
                            sw = min(0.9, sw + 0.025 + players[wi]["style"] - players[li]["style"] * 0.5)
                            sl = max(0.3, sl - 0.025 + players[li]["style"] - players[wi]["style"] * 0.5)
                            tot = int(rng.normal(165 if best_of == 3 else 260, 25))
                            wsv = max(30, tot // 2 + int(rng.integers(-6, 7)))
                            lsv = max(30, tot - wsv)
                            wwon, lwon = rng.binomial(wsv, sw), rng.binomial(lsv, sl)
                            w1in, l1in = rng.binomial(wsv, 0.62), rng.binomial(lsv, 0.62)
                            w1w, l1w = min(w1in, int(wwon * 0.74)), min(l1in, int(lwon * 0.74))
                            match_num += 1
                            rows.append({
                                "tourney_id": tid, "tourney_name": tname, "surface": surf, "draw_size": draw,
                                "tourney_level": level, "tourney_date": tdate.strftime("%Y%m%d"),
                                "match_num": match_num, "winner_name": players[wi]["name"],
                                "winner_ioc": players[wi]["ioc"], "loser_name": players[li]["name"],
                                "loser_ioc": players[li]["ioc"], "score": "", "best_of": best_of, "round": rname,
                                "w_svpt": wsv, "w_1stIn": w1in, "w_1stWon": w1w, "w_2ndWon": wwon - w1w,
                                "l_svpt": lsv, "l_1stIn": l1in, "l_1stWon": l1w, "l_2ndWon": lwon - l1w,
                                "winner_rank": int(rank[wi]), "winner_rank_points": int(rank_pts[wi]),
                                "loser_rank": int(rank[li]), "loser_rank_points": int(rank_pts[li]),
                            })
                            frac = {128: 0.005, 64: 0.025, 32: 0.05, 16: 0.1, 8: 0.2, 4: 0.36, 2: 0.6}[len(alive)]
                            points_log[li].append((abs_week, int(POINTS[level] * frac)))
                            if len(alive) == 2:
                                points_log[wi].append((abs_week, POINTS[level]))
                            nxt.append(wi)
                        alive = nxt
            path = out_dir / f"{tour}_matches_{year}.csv"
            with path.open("w", newline="") as fh:
                wr = csv.DictWriter(fh, fieldnames=COLUMNS)
                wr.writeheader()
                wr.writerows(rows)
            paths.append(path)
            for log in points_log:  # drop stale points
                log[:] = [(wk, pt) for wk, pt in log if (year + 1) * 53 - wk <= 60]
    return paths


if __name__ == "__main__":
    generate(Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw_synthetic"), range(2015, 2025))

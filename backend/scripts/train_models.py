#!/usr/bin/env python
"""Train AKERATEN tennis models.

1. Downloads Jeff Sackmann's tennis_atp / tennis_wta match CSVs (default 2015-2024)
   from raw.githubusercontent.com into backend/data/raw/ (cached, not committed).
   If the download fails (no network / blocked host) it falls back to a clearly
   labelled SYNTHETIC dataset (scripts/synthetic_tennis.py) so the pipeline still
   runs; artifacts then carry meta.source = "synthetic".
2. Walks all matches chronologically computing, BEFORE each match, the features
   (overall/surface Elo, rank, form-10, H2H, fatigue, serve/return points won)
   and then updating the ratings.
3. Trains logistic regression and gradient boosting (xgboost if installed, else
   sklearn HistGradientBoosting) on years <= test-2, selects on test-1 by
   log-loss, refits on train+val and reports accuracy / log-loss / Brier on the
   held-out test year, next to an Elo-only baseline.
4. Saves data/tennis_ratings.json (top players), data/tennis_ml.joblib and
   data/model_metrics.json.

Usage:  python scripts/train_models.py [--start 2015 --end 2024] [--synthetic] [--raw-dir DIR]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
import urllib.request
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from akeraten.models.tennis_elo import TennisElo, norm_surface  # noqa: E402
from akeraten.models.tennis_xgboost import FEATURES, HAS_XGBOOST, build_features  # noqa: E402

DATA = BACKEND / "data"
RAW_URL = "https://raw.githubusercontent.com/JeffSackmann/{repo}/master/{tour}_matches_{year}.csv"


def download(years, raw_dir: Path) -> bool:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for tour, repo in (("atp", "tennis_atp"), ("wta", "tennis_wta")):
        for y in years:
            dest = raw_dir / f"{tour}_matches_{y}.csv"
            if dest.exists() and dest.stat().st_size > 1000:
                continue
            url = RAW_URL.format(repo=repo, tour=tour, year=y)
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    dest.write_bytes(r.read())
                print(f"  downloaded {url}")
            except Exception as e:  # noqa: BLE001
                print(f"  ! could not download {url}: {e}")
                return False
    return True


def load_rows(raw_dir: Path, years) -> list[dict]:
    rows = []
    for tour in ("atp", "wta"):
        for y in years:
            p = raw_dir / f"{tour}_matches_{y}.csv"
            if not p.exists():
                continue
            with p.open(newline="", encoding="utf-8", errors="replace") as fh:
                for r in csv.DictReader(fh):
                    if not r.get("winner_name") or not r.get("loser_name") or not r.get("tourney_date"):
                        continue
                    sc = (r.get("score") or "").upper()
                    if "W/O" in sc or "WALKOVER" in sc or "DEF" in sc:
                        continue
                    r["tour"] = tour.upper()
                    rows.append(r)
    rows.sort(key=lambda r: (r["tourney_date"], r.get("tourney_id", ""), int(r.get("match_num") or 0)))
    return rows


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def _ordinal(d: str) -> int:
    return date(int(d[:4]), int(d[4:6]), int(d[6:8])).toordinal()


def run_pipeline(rows: list[dict], seed: int = 1):
    rng = np.random.default_rng(seed)
    elo = TennisElo()
    form = defaultdict(lambda: deque(maxlen=10))
    recent = defaultdict(lambda: deque(maxlen=30))
    serve = {}
    ret = {}
    last_rank = {}
    meta = {}
    h2h = defaultdict(lambda: [0, 0, []])
    X, y, yr, elo_p = [], [], [], []

    def pdict(name, rank):
        p = elo.player(name)
        return {"elo": p["elo"], "hard": p["hard"], "clay": p["clay"], "grass": p["grass"], "rank": rank,
                "form": list(form[name]), "serve": serve.get(name), "ret": ret.get(name)}

    for r in rows:
        w, l = r["winner_name"], r["loser_name"]
        d = r["tourney_date"]
        year = int(d[:4])
        o = _ordinal(d)
        surface = norm_surface(r.get("surface"))
        bo = _int(r.get("best_of")) or 3
        wr, lr = _int(r.get("winner_rank")), _int(r.get("loser_rank"))
        key = tuple(sorted((w, l)))
        hh = h2h[key]
        hw = hh[0] if key[0] == w else hh[1]
        hl = hh[1] if key[0] == w else hh[0]
        fw = sum(1 for t in recent[w] if o - t <= 14)
        fl = sum(1 for t in recent[l] if o - t <= 14)
        pw, pl = pdict(w, wr), pdict(l, lr)
        e = elo.predict(w, l, surface)["prob_a"]
        if rng.random() < 0.5:
            X.append(build_features(pw, pl, surface, bo, hw, hl, fw, fl)); y.append(1); elo_p.append(e)
        else:
            X.append(build_features(pl, pw, surface, bo, hl, hw, fl, fw)); y.append(0); elo_p.append(1 - e)
        yr.append(year)
        # ---- updates
        elo.update(w, l, surface)
        form[w].append(1)
        form[l].append(0)
        recent[w].append(o)
        recent[l].append(o)
        if wr:
            last_rank[w] = wr
        if lr:
            last_rank[l] = lr
        meta[w] = (r.get("tour"), r.get("winner_ioc"), d)
        meta[l] = (r.get("tour"), r.get("loser_ioc"), d)
        wsv, lsv = _int(r.get("w_svpt")), _int(r.get("l_svpt"))
        if wsv and lsv:
            ws = ((_int(r.get("w_1stWon")) or 0) + (_int(r.get("w_2ndWon")) or 0)) / wsv
            ls = ((_int(r.get("l_1stWon")) or 0) + (_int(r.get("l_2ndWon")) or 0)) / lsv
            a = 0.08
            serve[w] = (1 - a) * serve.get(w, ws) + a * ws
            serve[l] = (1 - a) * serve.get(l, ls) + a * ls
            ret[w] = (1 - a) * ret.get(w, 1 - ls) + a * (1 - ls)
            ret[l] = (1 - a) * ret.get(l, 1 - ws) + a * (1 - ws)
        if key[0] == w:
            hh[0] += 1
        else:
            hh[1] += 1
        hh[2].append({"date": f"{d[:4]}-{d[4:6]}-{d[6:]}", "tournament": r.get("tourney_name"),
                      "surface": surface, "winner": w, "score": r.get("score") or ""})
        hh[2] = hh[2][-3:]
    state = {"elo": elo, "form": form, "serve": serve, "ret": ret, "rank": last_rank, "meta": meta, "h2h": h2h}
    return np.array(X, dtype=float), np.array(y), np.array(yr), np.array(elo_p), state


def metrics(y, p) -> dict:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"n": int(len(y)), "accuracy": round(float(((p > 0.5) == (y == 1)).mean()), 4),
            "log_loss": round(float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()), 4),
            "brier": round(float(((p - y) ** 2).mean()), 4)}


def make_models():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    models = {"logistic": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000))}
    if HAS_XGBOOST:
        import xgboost as xgb

        models["xgboost"] = lambda: xgb.XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.04,
                                                      subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
                                                      eval_metric="logloss")
    else:
        from sklearn.ensemble import HistGradientBoostingClassifier

        models["hist_gradient_boosting"] = lambda: HistGradientBoostingClassifier(
            max_iter=250, learning_rate=0.04, max_depth=3, l2_regularization=1.0, min_samples_leaf=80)
    return models


def flip(X):
    """Mirror features (player order swap) for symmetric training."""
    return -X


def symmetric_predict(model, X):
    return 0.5 * (model.predict_proba(X)[:, 1] + 1 - model.predict_proba(flip(X))[:, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2015)
    ap.add_argument("--end", type=int, default=2024)
    ap.add_argument("--raw-dir", default=str(DATA / "raw"))
    ap.add_argument("--synthetic", action="store_true", help="skip download, use synthetic data")
    ap.add_argument("--top", type=int, default=1500)
    args = ap.parse_args()
    years = range(args.start, args.end + 1)
    raw_dir = Path(args.raw_dir)
    t0 = time.time()
    source = "sackmann"
    if args.synthetic or not download(years, raw_dir):
        source = "synthetic"
        raw_dir = DATA / "raw_synthetic"
        print("!! Using SYNTHETIC data (real Sackmann CSVs unavailable). Metrics are NOT real-world metrics.")
        from synthetic_tennis import generate

        if not all((raw_dir / f"{t}_matches_{y}.csv").exists() for t in ("atp", "wta") for y in years):
            generate(raw_dir, years)
    rows = load_rows(raw_dir, years)
    print(f"loaded {len(rows)} matches ({source}) in {time.time() - t0:.1f}s")
    X, y, yr, elo_p, st = run_pipeline(rows)
    test_year, val_year = args.end, args.end - 1
    burn = args.start + 2
    tr = (yr >= burn) & (yr < val_year)
    va = yr == val_year
    te = yr == test_year
    trva = (yr >= burn) & (yr < test_year)
    print(f"train {tr.sum()}  val {va.sum()}  test {te.sum()}")

    def fit(factory, mask):
        m = factory()
        Xa = np.vstack([X[mask], flip(X[mask])])
        ya = np.concatenate([y[mask], 1 - y[mask]])
        m.fit(Xa, ya)
        return m

    results = {"elo_baseline": {"val": metrics(y[va], elo_p[va]), "test": metrics(y[te], elo_p[te])}}
    best, best_ll = None, 9.0
    for name, factory in make_models().items():
        m = fit(factory, tr)
        mv = metrics(y[va], symmetric_predict(m, X[va]))
        m2 = fit(factory, trva)
        mt = metrics(y[te], symmetric_predict(m2, X[te]))
        results[name] = {"val": mv, "test": mt}
        print(f"{name:24s} val {mv}  test {mt}")
        if mv["log_loss"] < best_ll:
            best, best_ll, best_model = name, mv["log_loss"], m2
    print(f"{'elo_baseline':24s} val {results['elo_baseline']['val']}  test {results['elo_baseline']['test']}")
    print(f"selected: {best}")

    import joblib

    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    joblib.dump({"model": best_model, "kind": best, "features": FEATURES, "trained_on": source,
                 "years": [args.start, args.end], "created": created, "metrics": results[best]},
                DATA / "tennis_ml.joblib", compress=3)

    # ---- ratings JSON (top players)
    elo = st["elo"]
    keep = [n for n, p in elo.players.items() if p["n"] >= 10]
    keep.sort(key=lambda n: -elo.players[n]["elo"])
    keep = keep[: args.top]
    keep_set = set(keep)
    players = {}
    for n in keep:
        p = elo.players[n]
        tour, ioc, last = st["meta"].get(n, (None, None, None))
        players[n] = {"elo": round(p["elo"], 1), "hard": round(p["hard"], 1), "clay": round(p["clay"], 1),
                      "grass": round(p["grass"], 1), "n": p["n"], "rank": st["rank"].get(n), "tour": tour,
                      "country": ioc, "form": ["W" if x else "L" for x in st["form"][n]],
                      "serve": round(st["serve"][n], 4) if n in st["serve"] else None,
                      "ret": round(st["ret"][n], 4) if n in st["ret"] else None,
                      "last": f"{last[:4]}-{last[4:6]}-{last[6:]}" if last else None}
    top_h2h = set(keep[:400])
    pairs = [((a, b), v) for (a, b), v in st["h2h"].items()
             if a in top_h2h and b in top_h2h and v[0] + v[1] >= 2]
    pairs.sort(key=lambda kv: -(kv[1][0] + kv[1][1]))
    h2h = {f"{a}|{b}": [v[0], v[1], [{"date": x["date"], "tournament": x["tournament"], "score": x["score"],
                                       "winner": "a" if x["winner"] == a else "b"} for x in v[2][-2:]]]
           for (a, b), v in pairs[:6000]}
    out = TennisElo(players, {"source": source, "years": [args.start, args.end], "created": created,
                              "n_matches": len(rows), "note": "SYNTHETIC data - demo only" if source == "synthetic" else
                              "Jeff Sackmann tennis_atp/tennis_wta (CC BY-NC-SA 4.0)"})
    out.h2h = {k: v for k, v in h2h.items() if k.split("|")[0] in keep_set}
    out.save(DATA / "tennis_ratings.json")
    summary = {"source": source, "years": [args.start, args.end], "test_year": test_year, "val_year": val_year,
               "n_matches": len(rows), "selected_model": best, "results": results, "created": created,
               "features": FEATURES, "n_players_saved": len(players), "n_h2h_pairs": len(out.h2h)}
    (DATA / "model_metrics.json").write_text(json.dumps(summary, indent=2))
    for f in ("tennis_ratings.json", "tennis_ml.joblib", "model_metrics.json"):
        print(f"  {f}: {(DATA / f).stat().st_size / 1024:.0f} KB")
    print(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()

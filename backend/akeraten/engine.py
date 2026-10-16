"""Engine: ingest -> experts -> models -> value detection -> persistence -> snapshot.

One `tick()` runs a full cycle. The API only reads the immutable snapshot the
engine publishes at the end of each tick, so requests never block on models."""
from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

from . import value_detector as vd
from .config import DEFAULT_SETTINGS, RISK_PROFILES, TELEGRAM_MIN_EDGE, demo_mode
from .data_ingestion import DemoProvider, build_clients, merge_matches
from .data_ingestion.demo import SimMatch
from .db import Match, OddsSnapshot, Prediction, Setting, ValueBet, safe, session
from .expert_tracker import ExpertTracker
from .models.ensemble import get_ensemble
from .models.tennis_elo import get_tennis_elo
from .models.tt_elo import get_tt_elo
from .scheduler import telegram

log = logging.getLogger("akeraten.engine")
MARKET = "Ganador del partido"
MAX_ODDS = 10.0  # long shots: model error dominates, skip
HISTORY_LEN = 300


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime) -> str:
    return d.isoformat(timespec="seconds").replace("+00:00", "Z")


class Engine:
    def __init__(self, demo: bool | None = None, seed: int | None = None, persist: bool = True,
                 seed_history: bool = True):
        self.demo = demo_mode() if demo is None else demo
        self.persist = persist
        self.rng = random.Random(seed)
        self.ensemble = get_ensemble()
        self.provider = DemoProvider(seed=seed, anchor=self._anchor) if self.demo else None
        self.clients = build_clients()
        self.tracker = ExpertTracker(demo=self.demo, seed=seed, persist=persist)
        self.lock = threading.RLock()
        self.settings = dict(DEFAULT_SETTINGS)
        self._load_settings()
        self.matches: dict[str, dict] = {}
        self.predictions: dict[str, dict] = {}
        self.prob_history: dict[str, deque] = {}
        self.active: dict[str, dict] = {}  # bet_id -> current value bet (API view)
        self.bets: dict[str, dict] = {}  # bet_id -> placed (simulated) bet record, incl. history
        self.closing: dict[str, dict] = {}
        self.alerts: deque = deque(maxlen=100)
        self.pending_alerts: list[dict] = []
        self.tick_count = 0
        self.last_tick: str | None = None
        self.last_tick_ms = 0.0
        self._last_odds_snap: dict[str, tuple[float, tuple]] = {}
        self.snapshot = {"matches": [], "value_bets": [], "ts": None}
        if self.demo and seed_history:
            self._seed_demo_history()

    def _anchor(self, m: dict) -> float:
        """Demo only: the model's own pre-match estimate (no experts) used to anchor
        the simulator's hidden truth."""
        m = dict(m, status="upcoming", id=m.get("match_id"))
        return self.ensemble.predict(m, None)["prematch_a"]

    # ------------------------------------------------------------ settings
    @safe
    def _load_settings(self) -> None:
        if not self.persist:
            return
        with session() as s:
            row = s.get(Setting, "settings")
            if row and isinstance(row.value, dict):
                self.settings.update({k: v for k, v in row.value.items() if k in DEFAULT_SETTINGS})

    def update_settings(self, patch: dict) -> dict:
        patch = {k: v for k, v in (patch or {}).items() if k in DEFAULT_SETTINGS and v is not None}
        if "risk_profile" in patch:
            if patch["risk_profile"] not in RISK_PROFILES:
                raise ValueError("risk_profile must be conservador|moderado|agresivo")
            for k, v in RISK_PROFILES[patch["risk_profile"]].items():
                patch.setdefault(k, v)
        for k in ("bankroll", "kelly_fraction", "min_edge_tennis", "min_edge_tt", "suspicious_edge", "max_stake_pct"):
            if k in patch:
                patch[k] = float(patch[k])
                if patch[k] < 0:
                    raise ValueError(f"{k} must be >= 0")
        if "kelly_fraction" in patch and patch["kelly_fraction"] > 1:
            raise ValueError("kelly_fraction must be <= 1")
        if "max_stake_pct" in patch and patch["max_stake_pct"] > 1:
            raise ValueError("max_stake_pct must be <= 1")
        if "sports" in patch:
            sp = [s for s in patch["sports"] if s in ("tennis", "table_tennis")]
            patch["sports"] = sp or ["tennis", "table_tennis"]
        with self.lock:
            self.settings.update(patch)
        self._save_settings()
        return dict(self.settings)

    @safe
    def _save_settings(self) -> None:
        if not self.persist:
            return
        with session() as s:
            row = s.get(Setting, "settings")
            if row:
                row.value = dict(self.settings)
            else:
                s.add(Setting(key="settings", value=dict(self.settings)))

    # ------------------------------------------------------------ ingest
    def fetch(self) -> list[dict]:
        if self.demo:
            return self.provider.fetch()
        batches = []
        score_clients = [c for c in self.clients if c.enabled and c.provides_scores]
        odds_clients = [c for c in self.clients if c.enabled and not c.provides_scores]
        for c in score_clients + odds_clients:
            batches.append(c.fetch())
        return merge_matches(batches)

    def sources(self) -> list[dict]:
        out = [self.provider.info()] if self.demo else []
        for c in self.clients:
            i = c.info()
            if self.demo:
                i["status"] = "skipped (demo)" if c.enabled else "disabled (no key)"
            elif not c.enabled:
                i["status"] = "disabled (no key)"
            out.append({"name": i["name"], "enabled": bool(i["enabled"]), "status": i["status"],
                        "sports": i.get("sports"), "last_error": i.get("last_error")})
        return out

    # ------------------------------------------------------------ tick
    def tick(self) -> dict:
        t0 = time.perf_counter()
        raw = self.fetch()
        now = _now()
        new_alerts = []
        seen = set()
        with self.lock:
            for m in raw:
                mid = m["match_id"]
                seen.add(mid)
                m["id"] = mid
                prev = self.matches.get(mid)
                self._lifecycle(prev, m)
                if self.demo:
                    sim = self.provider.matches.get(mid)
                    if sim is not None:
                        self.tracker.demo_picks(m, sim.true_p)
                self.matches[mid] = m
            for mid in [k for k in self.matches if k not in seen]:
                self._drop(mid)
            for mid, m in self.matches.items():
                if m["status"] == "finished" and mid in self.predictions:
                    continue
                cons = self.tracker.consensus(mid)
                try:
                    pred = self.ensemble.predict(m, cons)
                except Exception as e:  # noqa: BLE001
                    log.warning("prediction failed for %s: %s", mid, e)
                    continue
                self.predictions[mid] = pred
                m["model_prob_a"], m["model_prob_b"] = pred["prob_a"], pred["prob_b"]
                self._history(mid, m, pred, now)
                if m["status"] != "finished":
                    new_alerts += self._detect(m, pred, now)
            for mid, m in self.matches.items():
                p = self.predictions.get(mid)
                if p:
                    m["model_prob_a"], m["model_prob_b"] = p["prob_a"], p["prob_b"]
                else:
                    m.setdefault("model_prob_a", None)
                    m.setdefault("model_prob_b", None)
                m["value_bet_count"] = sum(1 for b in self.active.values() if b["match_id"] == mid)
            self.tick_count += 1
            self.last_tick = _iso(now)
            self.snapshot = {"matches": self._sorted_matches(), "value_bets": self.value_bets(), "ts": self.last_tick}
        if self.persist:
            self._persist(now)
        for a in new_alerts:
            self.alerts.append(a)
            if a["edge"] > TELEGRAM_MIN_EDGE:
                telegram.send_alert(a)
        self.pending_alerts = new_alerts
        self.last_tick_ms = round((time.perf_counter() - t0) * 1000, 1)
        return self.snapshot

    def _drop(self, mid: str) -> None:
        self.matches.pop(mid, None)
        self.predictions.pop(mid, None)
        self.prob_history.pop(mid, None)
        for bid in [b for b, v in self.active.items() if v["match_id"] == mid]:
            self.active.pop(bid, None)

    def _lifecycle(self, prev: dict | None, m: dict) -> None:
        mid = m["id"]
        if prev and prev.get("status") == "upcoming" and m["status"] in ("live", "finished"):
            closing = prev.get("odds")
            if closing:
                self.capture_closing(mid, closing)
        if m["status"] == "finished" and (prev is None or prev.get("status") != "finished"):
            winner = m.get("winner") or self._infer_winner(m)
            m["winner"] = winner
            self._settle(mid, winner)
            self.tracker.settle(mid, winner)
            if prev is not None and winner in ("a", "b"):
                w, l = (m["player_a"], m["player_b"]) if winner == "a" else (m["player_b"], m["player_a"])
                if m["sport"] == "tennis":
                    get_tennis_elo().update(w, l, m.get("surface"))
                else:
                    get_tt_elo().update(w, l)

    @staticmethod
    def _infer_winner(m: dict) -> str | None:
        sc = m.get("score") or {}
        if m["sport"] == "table_tennis" and len(sc.get("games") or []) == 2:
            a, b = sc["games"]
            return "a" if a > b else "b" if b > a else None
        sw = sc.get("sets_won")
        if not sw:
            sets = sc.get("sets") or []
            sw = [sum(1 for x, y in sets if x > y), sum(1 for x, y in sets if y > x)]
        return "a" if sw[0] > sw[1] else "b" if sw[1] > sw[0] else None

    def capture_closing(self, mid: str, closing: dict) -> None:
        if mid in self.closing:
            return
        self.closing[mid] = closing
        self.tracker.on_match_live(mid, closing)
        for b in self.bets.values():
            if b["match_id"] == mid and not b["in_play"] and b.get("closing_odds") is None:
                b["closing_odds"] = closing["player_a" if b["selection_side"] == "a" else "player_b"]
                b["clv"] = vd.clv(b["entry_odds"], b["closing_odds"])
                self._store_bet(b)
        if self.persist:
            self._store_closing(mid, closing)

    def capture_due_closing_lines(self) -> int:
        """Scheduler job: for feeds that lag, freeze the closing line of upcoming
        matches whose start time has passed."""
        n = 0
        now = _now()
        with self.lock:
            for mid, m in self.matches.items():
                st = m.get("start_time")
                if m["status"] == "upcoming" and m.get("odds") and isinstance(st, str):
                    try:
                        if datetime.fromisoformat(st.replace("Z", "+00:00")) <= now and mid not in self.closing:
                            self.capture_closing(mid, m["odds"])
                            n += 1
                    except ValueError:
                        pass
        return n

    def _settle(self, mid: str, winner: str | None) -> None:
        for b in self.bets.values():
            if b["match_id"] == mid and b["result"] == "pending" and winner in ("a", "b"):
                won = b["selection_side"] == winner
                b["result"] = "win" if won else "loss"
                b["profit"] = round(b["stake"] * (b["entry_odds"] - 1) if won else -b["stake"], 2)
                b["settled_at"] = _iso(_now())
                self._store_bet(b)

    def _history(self, mid: str, m: dict, pred: dict, now: datetime) -> None:
        h = self.prob_history.setdefault(mid, deque(maxlen=HISTORY_LEN))
        fair = None
        if m.get("odds"):
            fair = vd.fair_probs(m["odds"]["player_a"], m["odds"]["player_b"])[0]
        point = {"t": _iso(now), "model_a": pred["prob_a"], "implied_a": None if fair is None else round(fair, 4)}
        if not h or h[-1]["model_a"] != point["model_a"] or h[-1]["implied_a"] != point["implied_a"]:
            h.append(point)

    # ------------------------------------------------------------ value detection
    def _detect(self, m: dict, pred: dict, now: datetime) -> list[dict]:
        mid = m["id"]
        odds = m.get("odds")
        sport = m["sport"]
        new = []
        for side in ("a", "b"):
            bid = f"vb-{mid}-{side}"
            ok = bool(odds) and sport in self.settings["sports"]
            if ok:
                o = odds["player_a" if side == "a" else "player_b"]
                other = odds["player_b" if side == "a" else "player_a"]
                p = pred["prob_a"] if side == "a" else pred["prob_b"]
                ev = vd.evaluate_side(side, p, o, other, sport, self.settings)
                ok = ev.is_value and o <= MAX_ODDS and p >= 0.08
            if not ok:
                self.active.pop(bid, None)
                continue
            comps = pred["components_a"]
            pre = pred["prematch_components_a"]
            flip = (lambda x: None if x is None else (x if side == "a" else 1 - x))  # noqa: E731
            models = {k: None if comps.get(k) is None else round(flip(comps[k]), 4)
                      for k in ("elo", "ml", "monte_carlo", "experts", "ensemble")}
            agree = [flip(pre.get(k)) for k in ("elo", "ml", "monte_carlo", "experts")]
            label, score = vd.confidence(agree + [flip(pred["prematch_a"])], pred["data_quality"], ev.suspicious)
            first = self.active.get(bid) or self.bets.get(bid)
            bet = {
                "id": bid, "match_id": mid, "sport": sport, "tournament": m.get("tournament"),
                "category": m.get("category"), "player_a": m["player_a"], "player_b": m["player_b"],
                "status": m["status"], "market": MARKET, "selection": m["player_a"] if side == "a" else m["player_b"],
                "selection_side": side, "odds": ev.odds, "bookmaker": m.get("bookmaker") or m.get("source"),
                "model_prob": round(ev.model_prob, 4), "implied_prob": round(ev.implied_prob, 4),
                "fair_prob": round(ev.fair_prob, 4) if ev.fair_prob is not None else None,
                "edge": round(ev.edge, 4), "kelly_full": round(ev.kelly_full, 4),
                "kelly_fraction": round(ev.kelly_fraction, 4), "stake": ev.stake, "confidence": label,
                "confidence_score": score, "suspicious": ev.suspicious,
                "created_at": first["created_at"] if first else _iso(now), "models": models,
                "source": m.get("source"), "in_play": m["status"] == "live",
            }
            is_new = bid not in self.active
            self.active[bid] = bet
            if bid not in self.bets:
                rec = dict(bet, entry_odds=ev.odds, entry_edge=bet["edge"], result="pending", profit=None,
                           closing_odds=None, clv=None, settled_at=None)
                self.bets[bid] = rec
                self._store_bet(rec)
            if is_new:
                new.append(bet)
        return new

    def value_bets(self, sport: str | None = None, min_edge: float | None = None) -> list[dict]:
        out = [b for b in self.active.values()
               if (not sport or b["sport"] == sport) and (min_edge is None or b["edge"] >= min_edge)]
        return sorted(out, key=lambda b: -b["edge"])

    def _sorted_matches(self) -> list[dict]:
        order = {"live": 0, "upcoming": 1, "finished": 2}
        return sorted(self.matches.values(), key=lambda m: (order.get(m["status"], 3), m.get("start_time") or "",
                                                            m["id"]))

    # ------------------------------------------------------------ persistence
    @safe
    def _store_bet(self, b: dict) -> None:
        if not self.persist:
            return
        with session() as s:
            row = s.get(ValueBet, b["id"])
            created = datetime.fromisoformat(b["created_at"].replace("Z", "+00:00"))
            fields = dict(match_id=b["match_id"], sport=b["sport"], tournament=b.get("tournament"),
                          category=b.get("category"), player_a=b["player_a"], player_b=b["player_b"],
                          market=b["market"], selection=b["selection"], selection_side=b["selection_side"],
                          odds=b["entry_odds"], bookmaker=b.get("bookmaker"), model_prob=b["model_prob"],
                          implied_prob=b["implied_prob"], fair_prob=b.get("fair_prob"), edge=b["entry_edge"],
                          kelly_full=b["kelly_full"], kelly_fraction=b["kelly_fraction"], stake=b["stake"],
                          confidence=b["confidence"], confidence_score=b["confidence_score"],
                          suspicious=b["suspicious"], in_play=b["in_play"], created_at=created,
                          closing_odds=b.get("closing_odds"), clv=b.get("clv"), result=b["result"],
                          profit=b.get("profit"), source=b.get("source") or "live", models=b.get("models"))
            if b.get("settled_at"):
                fields["settled_at"] = datetime.fromisoformat(b["settled_at"].replace("Z", "+00:00"))
            if row:
                for k, v in fields.items():
                    setattr(row, k, v)
            else:
                s.add(ValueBet(id=b["id"], **fields))

    @safe
    def _store_closing(self, mid: str, closing: dict) -> None:
        with session() as s:
            s.add(OddsSnapshot(match_id=mid, odds_a=closing["player_a"], odds_b=closing["player_b"],
                               status="closing", is_closing=True))

    @safe
    def _persist(self, now: datetime) -> None:
        ts = time.time()
        with session() as s:
            for mid, m in self.matches.items():
                o = m.get("odds")
                last = self._last_odds_snap.get(mid)
                key = (o["player_a"], o["player_b"]) if o else None
                changed = last is None or last[1] != key
                if not changed and ts - last[0] < 300:
                    continue
                if last is not None and ts - last[0] < 30 and m["status"] == (self.matches.get(mid) or {}).get("status"):
                    continue
                self._last_odds_snap[mid] = (ts, key)
                s.merge(Match(id=mid, sport=m["sport"], player_a=m["player_a"], player_b=m["player_b"],
                              tournament=m.get("tournament"), category=m.get("category"), surface=m.get("surface"),
                              status=m["status"], start_time=m.get("start_time") if isinstance(m.get("start_time"), str)
                              else None, best_of=m.get("best_of"), score=m.get("score"), winner=m.get("winner"),
                              source=m.get("source")))
                if o:
                    s.add(OddsSnapshot(match_id=mid, odds_a=o["player_a"], odds_b=o["player_b"],
                                       bookmaker=m.get("bookmaker"), status=m["status"]))
                p = self.predictions.get(mid)
                if p:
                    c = p["components_a"]
                    s.add(Prediction(match_id=mid, prob_a=p["prob_a"], elo=c.get("elo"), ml=c.get("ml"),
                                     monte_carlo=c.get("monte_carlo"), experts=c.get("experts"), status=m["status"]))

    @safe
    def cleanup_db(self, days: int = 7) -> None:
        cutoff = _now() - timedelta(days=days)
        with session() as s:
            s.query(OddsSnapshot).filter(OddsSnapshot.ts < cutoff, OddsSnapshot.is_closing.is_(False)).delete()
            s.query(Prediction).filter(Prediction.ts < cutoff).delete()

    # ------------------------------------------------------------ demo history
    def _seed_demo_history(self, n_candidates: int = 900) -> None:
        """Simulated past bets (tagged demo) produced by the same mechanism as the
        live demo: the model is compared with a noisy simulated bookmaker and the
        outcome is drawn from the hidden TRUE probability, so the resulting ROI /
        CLV can be positive or negative - nothing is rigged."""
        prov = DemoProvider(seed=self.rng.randint(0, 10**9), anchor=self._anchor)
        now = _now()
        cats = [("tennis", c) for c in ("ATP", "WTA", "Challenger", "ITF")] + \
               [("table_tennis", c) for c in ("WTT", "ITTF", "Setka Cup", "TT Elite Series", "Czech Liga Pro")]
        prov.matches.clear()
        made = 0
        for i in range(n_candidates):
            sport, cat = self.rng.choice(cats)
            sim: SimMatch | None = prov._new_match(sport, cat, now)
            if sim is None:
                continue
            m = sim.to_common()
            m["id"] = m["match_id"]
            odds = m.get("odds")
            if not odds:
                continue
            pred = self.ensemble.predict(m, None)
            for side in ("a", "b"):
                o = odds["player_a" if side == "a" else "player_b"]
                other = odds["player_b" if side == "a" else "player_a"]
                p = pred["prob_a"] if side == "a" else pred["prob_b"]
                ev = vd.evaluate_side(side, p, o, other, sport, self.settings)
                if not (ev.is_value and o <= MAX_ODDS):
                    continue
                true_side = sim.true_p if side == "a" else 1 - sim.true_p
                # closing line: the market moves part of the way towards the truth
                q_open = 1 / (o * (1 + sim.margin))  # bookmaker's (noisy) probability
                lq = math.log(q_open / (1 - q_open))
                lt = math.log(true_side / (1 - true_side))
                q_close = 1 / (1 + math.exp(-(lq + 0.35 * (lt - lq) + self.rng.gauss(0, 0.05))))
                closing = round(max(1.01, 1 / (q_close * (1 + sim.margin))), 2)
                won = self.rng.random() < true_side
                created = now - timedelta(days=self.rng.uniform(0.3, 21))
                label, score = vd.confidence([p], pred["data_quality"], ev.suspicious)
                bid = f"vb-hist-{i}-{side}"
                self.bets[bid] = {
                    "id": bid, "match_id": f"hist-{i}", "sport": sport, "tournament": m.get("tournament"),
                    "category": cat, "player_a": m["player_a"], "player_b": m["player_b"], "status": "finished",
                    "market": MARKET, "selection": m["player_a"] if side == "a" else m["player_b"],
                    "selection_side": side, "odds": o, "entry_odds": o, "bookmaker": m.get("bookmaker"),
                    "model_prob": round(p, 4), "implied_prob": round(ev.implied_prob, 4),
                    "fair_prob": round(ev.fair_prob, 4), "edge": round(ev.edge, 4), "entry_edge": round(ev.edge, 4),
                    "kelly_full": round(ev.kelly_full, 4), "kelly_fraction": round(ev.kelly_fraction, 4),
                    "stake": ev.stake, "confidence": label, "confidence_score": score, "suspicious": ev.suspicious,
                    "created_at": _iso(created), "models": None, "source": "demo", "in_play": False,
                    "closing_odds": closing, "clv": vd.clv(o, closing), "result": "win" if won else "loss",
                    "profit": round(ev.stake * (o - 1) if won else -ev.stake, 2),
                    "settled_at": _iso(created + timedelta(hours=self.rng.uniform(1, 4))),
                }
                made += 1
        log.info("seeded %d simulated historical value bets", made)

    # ------------------------------------------------------------ stats
    def stats(self) -> dict:
        with self.lock:
            bets = list(self.bets.values())
        settled = sorted([b for b in bets if b["result"] in ("win", "loss")], key=lambda b: b["settled_at"])
        clvs = [b["clv"] for b in bets if b.get("clv") is not None]
        staked = sum(b["stake"] for b in settled)
        profit = sum(b["profit"] or 0 for b in settled)
        bank0 = float(self.settings["bankroll"])
        curve, bank = [], bank0
        if settled:
            curve.append({"t": settled[0]["created_at"], "bankroll": round(bank0, 2)})
        for b in settled:
            bank += b["profit"] or 0
            curve.append({"t": b["settled_at"], "bankroll": round(bank, 2)})
        if len(curve) > 400:  # thin out for the chart
            step = len(curve) / 400
            curve = [curve[int(i * step)] for i in range(400)] + [curve[-1]]

        def block(bs: list[dict]) -> dict:
            st = [b for b in bs if b["result"] in ("win", "loss")]
            cl = [b["clv"] for b in bs if b.get("clv") is not None]
            stk = sum(b["stake"] for b in st)
            return {"n_value_bets": len(bs), "n_settled": len(st),
                    "avg_edge": round(sum(b["entry_edge"] for b in bs) / len(bs), 4) if bs else 0.0,
                    "avg_clv": round(sum(cl) / len(cl), 4) if cl else None,
                    "hit_rate": round(sum(b["result"] == "win" for b in st) / len(st), 4) if st else None,
                    "roi_sim": round(sum(b["profit"] or 0 for b in st) / stk, 4) if stk else None,
                    "profit": round(sum(b["profit"] or 0 for b in st), 2)}

        return {
            "n_value_bets": len(bets), "n_settled": len(settled), "n_active": len(self.active),
            "avg_edge": round(sum(b["entry_edge"] for b in bets) / len(bets), 4) if bets else 0.0,
            "avg_clv": round(sum(clvs) / len(clvs), 4) if clvs else None,
            "clv_positive_pct": round(sum(c > 0 for c in clvs) / len(clvs), 4) if clvs else None,
            "clv_values": [round(b["clv"], 4) for b in sorted(
                (b for b in bets if b.get("clv") is not None), key=lambda b: b["created_at"])][-200:],
            "roi_sim": round(profit / staked, 4) if staked else None,
            "profit_sim": round(profit, 2), "bankroll_start": bank0, "bankroll_curve": curve,
            "by_sport": {s: block([b for b in bets if b["sport"] == s]) for s in ("tennis", "table_tennis")},
            "hit_rate": round(sum(b["result"] == "win" for b in settled) / len(settled), 4) if settled else None,
            "mode": "demo" if self.demo else "live",
            "note": "Simulación (apuestas ficticias, flat a stake Kelly). Rendimientos pasados no garantizan "
                    "resultados futuros." + (" Datos DEMO simulados." if self.demo else ""),
        }

    # ------------------------------------------------------------ detail views
    def match_detail(self, mid: str) -> dict | None:
        with self.lock:
            m = self.matches.get(mid)
            if not m:
                return None
            d = dict(m)
            pred = self.predictions.get(mid) or {}
            hist = list(self.prob_history.get(mid, []))
        if m["sport"] == "tennis":
            elo = get_tennis_elo()
            h2h = pred.get("h2h") or elo.head_to_head(m["player_a"], m["player_b"])
            fa = d.get("form_a") or elo.player(m["player_a"]).get("form") or []
            fb = d.get("form_b") or elo.player(m["player_b"]).get("form") or []
        else:
            h2h = {"a": 0, "b": 0, "last": []}
            fa, fb = d.get("form_a") or [], d.get("form_b") or []
        d["h2h"] = {"a": h2h.get("a", 0), "b": h2h.get("b", 0), "last": h2h.get("last", [])}
        d["stats"] = d.get("stats") or {}
        d["prob_history"] = hist
        d["form_a"] = ["W" if x in ("W", 1) else "L" for x in fa][-10:]
        d["form_b"] = ["W" if x in ("W", 1) else "L" for x in fb][-10:]
        d["closing_odds"] = self.closing.get(mid)
        d["experts"] = self.tracker.consensus(mid)
        d["value_bets"] = [b for b in self.active.values() if b["match_id"] == mid]
        return d

    def predict_detail(self, mid: str, iterations: int = 10_000) -> dict | None:
        with self.lock:
            m = self.matches.get(mid)
            if not m:
                return None
            m = dict(m)
        cons = self.tracker.consensus(mid)
        p = self.ensemble.predict(m, cons, iterations=iterations, seed=abs(hash(mid)) % (2**31))
        p["breakdown"]["monte_carlo"]["iterations"] = iterations
        p["breakdown"]["experts"]["picks"] = cons.get("picks", [])
        return {"match_id": mid, "prob_a": p["prob_a"], "prob_b": p["prob_b"], "breakdown": p["breakdown"],
                "weights": p["weights"], "explanation": p["explanation"], "player_a": m["player_a"],
                "player_b": m["player_b"], "status": m["status"], "sport": m["sport"],
                "data_quality": p["data_quality"]}

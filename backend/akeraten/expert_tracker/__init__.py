"""Expert tracker: loads the expert list, collects their picks (real sources or
simulated in demo mode), builds a weighted consensus per match and tracks
hit-rate / CLV per expert."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import random
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..db import ExpertPrediction, safe, session
from ..players import TT_MEN, TT_WOMEN, WTA, ATP
from .nlp import extract_picks
from .sources import DISCORD_INBOX, FETCHERS, platform_enabled

log = logging.getLogger("akeraten.experts")
HERE = Path(__file__).resolve().parent
EXPERTS_PATH = HERE / "experts.json"
EXTRA_EXPERTS_PATH = HERE / "extra_experts.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime) -> str:
    return d.isoformat(timespec="seconds").replace("+00:00", "Z")


def load_experts(path: Path = EXPERTS_PATH, extra: Path = EXTRA_EXPERTS_PATH) -> list[dict]:
    """experts.json + extra_experts.json (schema: name, sport, platform, url, weight
    [, handle, uid, env, lang]). Later entries with the same name override earlier ones."""
    out: dict[str, dict] = {}
    for p in (path, extra):
        try:
            data = json.loads(Path(p).read_text()) if Path(p).exists() else []
        except json.JSONDecodeError:
            log.warning("invalid JSON in %s", p)
            data = []
        for e in data if isinstance(data, list) else []:
            if not isinstance(e, dict) or not e.get("name"):
                continue
            e.setdefault("sport", "tennis")
            e.setdefault("platform", "website")
            e.setdefault("url", "")
            e["weight"] = float(e.get("weight", 1.0))
            out[e["name"]] = e
    return list(out.values())


def _covers(expert: dict, sport: str) -> bool:
    return expert.get("sport") in (sport, "both", "all")


def _skill(name: str) -> float:
    """Demo only: hidden noise level of an expert's (simulated) opinions."""
    h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16) / 0xFFFFFF
    return 0.35 + 0.55 * h


class ExpertTracker:
    def __init__(self, demo: bool = True, seed: int | None = None, persist: bool = True):
        self.demo = demo
        self.persist = persist
        self.rng = random.Random(seed)
        self.experts = load_experts()
        self.picks: list[dict] = []
        self._by_match: dict[str, list[dict]] = {}
        self._seen_posts: set[str] = set()
        self.lock = threading.RLock()
        self.status: dict[str, str] = {}
        self._hr_cache: dict[str, tuple] = {}
        if demo:
            self._seed_history()
        else:
            self._load_db()

    # ----------------------------------------------------------- storage
    def add_pick(self, expert: str, match: dict, side: str, confidence: float, odds: float | None = None,
                 source: str = "live", ts: datetime | None = None, result: str = "pending",
                 closing_odds: float | None = None, text: str | None = None, store: bool = True) -> dict | None:
        mid = match.get("id") or match.get("match_id")
        with self.lock:
            if any(p["expert"] == expert for p in self._by_match.get(mid, [])):
                return None
            pick = {"expert": expert, "match_id": mid, "match": f"{match['player_a']} vs {match['player_b']}",
                    "sport": match.get("sport"), "side": side,
                    "predicted_winner": match["player_a"] if side == "a" else match["player_b"],
                    "confidence": round(float(confidence), 3), "timestamp": _iso(ts or _now()), "odds": odds,
                    "closing_odds": closing_odds, "result": result, "source": source}
            self.picks.append(pick)
            self._by_match.setdefault(mid, []).append(pick)
            if result != "pending":
                self._hr_cache.pop(expert, None)
        if store and self.persist:
            self._store(pick, text)
        return pick

    @safe
    def _store(self, p: dict, text: str | None = None) -> None:
        with session() as s:
            s.add(ExpertPrediction(expert=p["expert"], match_id=p["match_id"], match=p["match"], sport=p["sport"],
                                   predicted_winner=p["predicted_winner"], side=p["side"], confidence=p["confidence"],
                                   timestamp=datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00")),
                                   odds=p["odds"], closing_odds=p["closing_odds"], result=p["result"],
                                   source=p["source"], text=text))

    @safe
    def _update_db(self, p: dict) -> None:
        with session() as s:
            row = s.query(ExpertPrediction).filter_by(expert=p["expert"], match_id=p["match_id"]).first()
            if row:
                row.result, row.closing_odds = p["result"], p["closing_odds"]

    @safe
    def _load_db(self) -> None:
        with session() as s:
            rows = s.query(ExpertPrediction).filter(ExpertPrediction.source != "demo") \
                .order_by(ExpertPrediction.timestamp.desc()).limit(5000).all()
            for r in reversed(rows):
                p = {"expert": r.expert, "match_id": r.match_id, "match": r.match, "sport": r.sport, "side": r.side,
                     "predicted_winner": r.predicted_winner, "confidence": r.confidence,
                     "timestamp": _iso(r.timestamp.replace(tzinfo=r.timestamp.tzinfo or timezone.utc)),
                     "odds": r.odds, "closing_odds": r.closing_odds, "result": r.result, "source": r.source}
                self.picks.append(p)
                self._by_match.setdefault(r.match_id, []).append(p)

    # ----------------------------------------------------------- demo
    def _seed_history(self) -> None:
        """Simulated past picks so hit-rate / CLV are populated in demo mode.
        Outcomes are drawn from a hidden 'true' probability, NOT from the pick."""
        pools = {"tennis": [x[0] for x in ATP + WTA], "table_tennis": [x[0] for x in TT_MEN + TT_WOMEN]}
        now = _now()
        for e in self.experts:
            sports = [s for s in ("tennis", "table_tennis") if _covers(e, s)]
            n = self.rng.randint(25, 60)
            for k in range(n):
                sport = self.rng.choice(sports)
                a, b = self.rng.sample(pools[sport], 2)
                true_p = min(0.9, max(0.1, self.rng.betavariate(3, 3)))
                side, conf = self._opinion(e["name"], true_p)
                p_side = true_p if side == "a" else 1 - true_p
                q = 1 / (1 + math.exp(-(math.log(p_side / (1 - p_side)) + self.rng.gauss(0, 0.15))))
                odds = round(1 / (q * 1.055), 2)
                closing = round(odds * math.exp(self.rng.gauss(0.01 * (0.7 - _skill(e["name"])) * 3, 0.05)), 2)
                res = "win" if self.rng.random() < p_side else "loss"
                ts = now - timedelta(days=self.rng.uniform(0.5, 30))
                fake = {"id": f"demo-hist-{e['name'][:6]}-{k}", "player_a": a, "player_b": b, "sport": sport}
                self.add_pick(e["name"], fake, side, conf, odds, "demo", ts, res, max(1.01, closing), store=False)

    def _opinion(self, name: str, true_p: float) -> tuple[str, float]:
        x = math.log(true_p / (1 - true_p)) + self.rng.gauss(0, _skill(name))
        side = "a" if x >= 0 else "b"
        conf = min(0.85, max(0.52, 1 / (1 + math.exp(-abs(x)))))
        return side, round(conf, 3)

    def demo_picks(self, match: dict, true_p: float) -> list[dict]:
        """Each covering expert posts a pick on a given match with ~30% probability
        (decided once per expert/match)."""
        if match.get("status") == "finished":
            return []
        mid = match.get("id") or match.get("match_id")
        key = f"decided:{mid}"
        if key in self._seen_posts:
            return []
        self._seen_posts.add(key)
        out = []
        for e in self.experts:
            if not _covers(e, match["sport"]) or self.rng.random() > 0.3:
                continue
            side, conf = self._opinion(e["name"], true_p)
            odds = (match.get("odds") or {}).get("player_a" if side == "a" else "player_b")
            p = self.add_pick(e["name"], match, side, conf, odds, "demo")
            if p:
                out.append(p)
        return out

    # ----------------------------------------------------------- live
    def poll_sources(self, matches: list[dict]) -> int:
        """Fetch recent posts from every enabled platform and extract picks."""
        live = [m for m in matches if m.get("status") in ("upcoming", "live")]
        n = 0
        for e in self.experts:
            if not platform_enabled(e):
                self.status[e["name"]] = "disabled"
                continue
            try:
                posts = FETCHERS[e["platform"]](e)
                self.status[e["name"]] = "ok"
            except Exception as ex:  # noqa: BLE001
                self.status[e["name"]] = f"error: {str(ex)[:120]}"
                continue
            for post in posts:
                pid = f"{e['name']}:{post.get('id')}"
                if pid in self._seen_posts:
                    continue
                self._seen_posts.add(pid)
                for pk in extract_picks(post.get("text", ""), [m for m in live if _covers(e, m["sport"])]):
                    m = next(x for x in live if (x.get("id") or x.get("match_id")) == pk["match_id"])
                    odds = (m.get("odds") or {}).get("player_a" if pk["side"] == "a" else "player_b")
                    if self.add_pick(e["name"], m, pk["side"], pk["confidence"], odds, "live", text=post.get("text")):
                        n += 1
        return n

    def ingest_discord(self, payload: dict) -> dict:
        """Discord webhook-in: {"username"/"expert": str, "content": str}."""
        msg = {"id": payload.get("id") or str(hash(payload.get("content", ""))),
               "expert": payload.get("expert") or payload.get("username") or "VeloriumIQ",
               "text": payload.get("content") or payload.get("text") or "", "timestamp": _iso(_now()), "url": None}
        DISCORD_INBOX.append(msg)
        return msg

    # ----------------------------------------------------------- lifecycle
    def on_match_live(self, match_id: str, closing: dict | None) -> None:
        if not closing:
            return
        for p in self._by_match.get(match_id, []):
            if p["closing_odds"] is None:
                p["closing_odds"] = closing.get("player_a" if p["side"] == "a" else "player_b")
                if self.persist and p["source"] != "demo":
                    self._update_db(p)

    def settle(self, match_id: str, winner: str | None) -> None:
        if winner not in ("a", "b"):
            return
        for p in self._by_match.get(match_id, []):
            if p["result"] == "pending":
                p["result"] = "win" if p["side"] == winner else "loss"
                self._hr_cache.pop(p["expert"], None)
                if self.persist:
                    self._update_db(p)

    # ----------------------------------------------------------- outputs
    def hit_rate(self, name: str) -> tuple[float | None, int]:
        if name not in self._hr_cache:
            self._hr_cache[name] = self._hit_rate(name)
        return self._hr_cache[name]

    def _hit_rate(self, name: str) -> tuple[float | None, int]:
        settled = [p for p in self.picks if p["expert"] == name and p["result"] in ("win", "loss")]
        if not settled:
            return None, 0
        return sum(p["result"] == "win" for p in settled) / len(settled), len(settled)

    def consensus(self, match_id: str) -> dict:
        picks = self._by_match.get(match_id, [])
        if not picks:
            return {"consensus_a": None, "n": 0, "picks": []}
        weights = {e["name"]: e["weight"] for e in self.experts}
        num = den = 0.0
        for p in picks:
            hr, n = self.hit_rate(p["expert"])
            rel = ((hr or 0.5) * n + 0.5 * 20) / (n + 20)  # shrunk hit-rate
            w = weights.get(p["expert"], 1.0) * (0.5 + rel)
            pa = p["confidence"] if p["side"] == "a" else 1 - p["confidence"]
            num += w * pa
            den += w
        avg = num / den
        n = len(picks)
        cons = 0.5 + (avg - 0.5) * n / (n + 1)  # few picks -> weaker signal
        return {"consensus_a": round(cons, 4), "n": n,
                "picks": [{"expert": p["expert"], "predicted_winner": p["predicted_winner"],
                           "confidence": p["confidence"]} for p in picks]}

    def summary(self) -> list[dict]:
        out = []
        for e in self.experts:
            mine = [p for p in self.picks if p["expert"] == e["name"]]
            hr, n_settled = self.hit_rate(e["name"])
            clvs = [p["odds"] / p["closing_odds"] - 1 for p in mine if p.get("odds") and p.get("closing_odds")]
            recent = sorted(mine, key=lambda p: p["timestamp"], reverse=True)[:10]
            out.append({
                "name": e["name"], "sport": e["sport"], "platform": e["platform"], "url": e.get("url"),
                "weight": e["weight"], "hit_rate": None if hr is None else round(hr, 4), "n_picks": len(mine),
                "n_settled": n_settled, "clv": round(sum(clvs) / len(clvs), 4) if clvs else None,
                "status": "demo" if self.demo else self.status.get(e["name"], "disabled" if not platform_enabled(e) else "idle"),
                "recent": [{"match_id": p["match_id"], "match": p["match"], "predicted_winner": p["predicted_winner"],
                            "confidence": p["confidence"], "timestamp": p["timestamp"], "result": p["result"],
                            "source": p["source"]} for p in recent],
            })
        return out

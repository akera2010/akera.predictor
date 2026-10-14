"""Ensemble: Elo + ML + Monte Carlo + expert consensus.

Design (kept deliberately simple and conservative):
  1. Pre-match strength = weighted average in LOGIT space of the available
     components (Elo, ML, stats-based Markov/Monte Carlo, expert consensus).
     Missing components are dropped and weights renormalised.
  2. If the match is live, the pre-match strength is converted into serve-point
     probabilities and the point-level Markov/Monte Carlo model is run from the
     CURRENT score; that in-play probability is the final estimate (the score
     carries most of the information during a match).
  3. The result is clipped to [0.02, 0.98] - no model deserves more certainty.
"""
from __future__ import annotations

import math

from ..players import tennis_player_index, tt_player_index
from . import monte_carlo as mc
from .tennis_elo import get_tennis_elo, norm_surface
from .tennis_xgboost import get_tennis_ml
from .tt_elo import get_tt_elo

P_MIN, P_MAX = 0.02, 0.98
DEFAULT_WEIGHTS = {
    "tennis": {"elo": 0.30, "ml": 0.35, "monte_carlo": 0.20, "experts": 0.15},
    "table_tennis": {"elo": 0.45, "ml": 0.25, "monte_carlo": 0.0, "experts": 0.30},
}
_TENNIS_IDX = tennis_player_index()
_TT_IDX = tt_player_index()


def logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def clip(p: float) -> float:
    return min(max(p, P_MIN), P_MAX)


def blend(components: dict[str, float | None], weights: dict[str, float]) -> tuple[float, dict]:
    used = {k: w for k, w in weights.items() if w > 0 and components.get(k) is not None}
    tot = sum(used.values())
    if not tot:
        return 0.5, {}
    norm_w = {k: round(w / tot, 4) for k, w in used.items()}
    x = sum(norm_w[k] * logit(components[k]) for k in norm_w)
    return sigmoid(x), norm_w


def _pct(p: float | None) -> str:
    return "n/d" if p is None else f"{100 * p:.1f}%"


def tour_of(match: dict) -> str:
    cat = match.get("category")
    if cat in ("ATP", "WTA"):
        return cat
    info = _TENNIS_IDX.get(match.get("player_a", ""))
    if info:
        return info["tour"]
    t = (match.get("tournament") or "").upper()
    return "WTA" if "WTA" in t or " W" in t else "ATP"


def _form_score(form) -> float | None:
    if not form:
        return None
    return (sum(1 for x in form if x in ("W", 1)) + 2.5) / (len(form) + 5)


class Ensemble:
    def __init__(self, weights: dict | None = None):
        self.weights = weights or DEFAULT_WEIGHTS
        from .repos import load_repo_wrappers

        self.external = [w for w in load_repo_wrappers() if w.weight > 0]

    # ------------------------------------------------------------ tennis
    def _tennis_components(self, m: dict) -> dict:
        elo = get_tennis_elo()
        ml = get_tennis_ml()
        a, b = m["player_a"], m["player_b"]
        surface = norm_surface(m.get("surface"))
        e = elo.predict(a, b, surface, m.get("rank_a"), m.get("rank_b"))
        pa, pb = dict(elo.player(a, m.get("rank_a"))), dict(elo.player(b, m.get("rank_b")))
        pa.setdefault("rank", m.get("rank_a"))
        pb.setdefault("rank", m.get("rank_b"))
        h2h = elo.head_to_head(a, b)
        ml_p = ml.predict(pa, pb, surface, m.get("best_of") or 3, h2h) if ml.available else None
        tour = tour_of(m)
        base = mc.serve_base("tennis", tour)
        stats_p, sp = None, None
        if pa.get("serve") and pb.get("serve") and pa.get("ret") and pb.get("ret"):
            # Barnett-Clarke style combination of serve and return ability
            # deviations are shrunk (x0.6) towards the tour mean: raw rolling serve/return
            # stats are noisy and the Markov chain amplifies small differences.
            k = 0.6
            spa = base + k * ((pa["serve"] - base) - (pb["ret"] - (1 - base)))
            spb = base + k * ((pb["serve"] - base) - (pa["ret"] - (1 - base)))
            sp = (mc._r(spa), mc._r(spb))
            stats_p = mc.prematch_prob_exact(sp[0], sp[1], "tennis", m.get("best_of") or 3)
        known = (0.5 if e["known_a"] else 0) + (0.5 if e["known_b"] else 0)
        return {"elo": e, "ml": ml_p, "ml_kind": ml.name, "stats_prob": stats_p, "stats_serve": sp,
                "h2h": h2h, "tour": tour, "known": known, "surface": surface}

    # ------------------------------------------------------- table tennis
    def _tt_components(self, m: dict) -> dict:
        tt = get_tt_elo()
        e = tt.predict(m["player_a"], m["player_b"], m.get("rank_a"), m.get("rank_b"), m.get("best_of") or 5)
        ra, rb = m.get("rank_a"), m.get("rank_b")
        fa, fb = _form_score(m.get("form_a")), _form_score(m.get("form_b"))
        ml_p = None
        if ra and rb:
            x = 0.30 * math.log(rb / ra)
            if fa is not None and fb is not None:
                x += 1.5 * (fa - fb)
            ml_p = sigmoid(x)
        known = (0.5 if e["known_a"] else 0) + (0.5 if e["known_b"] else 0)
        return {"elo": e, "ml": ml_p, "ml_kind": "tt_rank_form_logit", "stats_prob": None, "stats_serve": None,
                "h2h": None, "tour": None, "known": known, "surface": None}

    # ------------------------------------------------------------- public
    def predict(self, match: dict, experts: dict | None = None, iterations: int | None = None,
                seed: int | None = None) -> dict:
        sport = match.get("sport", "tennis")
        best_of = match.get("best_of") or (5 if sport == "table_tennis" else 3)
        c = self._tt_components(match) if sport == "table_tennis" else self._tennis_components(match)
        exp_p = experts.get("consensus_a") if experts and experts.get("n") else None
        comps = {"elo": c["elo"]["prob_a"], "ml": c["ml"], "monte_carlo": c["stats_prob"], "experts": exp_p}
        weights = dict(self.weights[sport])
        ext = {}
        for w in self.external:  # optional third-party repos (off unless weight > 0 and adapter present)
            if w.sport == sport and w.available:
                p = w.predict_match(match["player_a"], match["player_b"], match.get("surface"), match.get("tournament"))
                if p is not None:
                    ext[w.name] = p
                    comps[f"ext:{w.name}"] = p
                    weights[f"ext:{w.name}"] = w.weight
        pre, used_w = blend(comps, weights)
        comps = {k: v for k, v in comps.items() if not k.startswith("ext:")}
        tour = c["tour"]
        spa, spb = mc.serve_probs_for(pre, sport, best_of, tour)
        status = match.get("status")
        st = mc.state_from_score(sport, match.get("score"), match.get("server"), best_of, status or "upcoming")
        live = status == "live"
        if iterations:
            sim = mc.simulate(spa, spb, st if live else None, sport, best_of, iterations, seed)
            mc_live = sim["prob_a"]
        else:
            sim = None
            mc_live = mc.inplay_prob_exact(spa, spb, st) if live else mc.prematch_prob_exact(spa, spb, sport, best_of)
        if status == "finished":
            final = 1.0 if (match.get("winner") == "a") else 0.0 if match.get("winner") == "b" else pre
        else:
            final = mc_live if live else pre
        final = clip(final) if status != "finished" else final
        mc_component = mc_live if live else (c["stats_prob"] if c["stats_prob"] is not None else mc_live)

        quality = 0.35 * c["known"] + (0.2 if c["ml"] is not None else 0) + (0.15 if exp_p is not None else 0) \
            + (0.15 if c["stats_prob"] is not None or sport == "table_tennis" else 0) \
            + (0.15 if match.get("odds") else 0)
        explanation = self._explain(match, c, comps, pre, final, live, st, iterations, experts)
        breakdown = {
            "elo": {"prob_a": round(c["elo"]["prob_a"], 4), "elo_a": c["elo"]["elo_a"], "elo_b": c["elo"]["elo_b"],
                    **({"surface_elo_a": c["elo"]["surface_elo_a"], "surface_elo_b": c["elo"]["surface_elo_b"],
                        "surface": c["surface"]} if sport == "tennis" else {})},
            "ml": {"prob_a": None if c["ml"] is None else round(c["ml"], 4), "model": c["ml_kind"]},
            "monte_carlo": {"prob_a": round(mc_component, 4), "in_play": live,
                            "iterations": sim["iterations"] if sim else 0,
                            "method": "monte_carlo" if sim else "markov_exact",
                            "set_score_dist": sim["set_score_dist"] if sim else {},
                            "serve_probs": {"a": spa, "b": spb},
                            "stats_prematch_prob_a": None if c["stats_prob"] is None else round(c["stats_prob"], 4)},
            "experts": {"consensus_a": None if exp_p is None else round(exp_p, 4),
                        "n": (experts or {}).get("n", 0)},
            "prematch_ensemble_a": round(pre, 4),
            "external": {k: round(v, 4) for k, v in ext.items()},
        }
        return {"match_id": match.get("id") or match.get("match_id"), "prob_a": round(final, 4),
                "prob_b": round(1 - final, 4), "prematch_a": round(pre, 4), "breakdown": breakdown,
                "weights": used_w, "explanation": explanation, "data_quality": round(min(1.0, quality), 3),
                "components_a": {"elo": c["elo"]["prob_a"], "ml": c["ml"], "monte_carlo": mc_component,
                                 "experts": exp_p, "ensemble": final},
                "prematch_components_a": comps, "h2h": c["h2h"]}

    @staticmethod
    def _explain(m, c, comps, pre, final, live, st, iterations, experts) -> list[str]:
        a, b = m["player_a"], m["player_b"]
        out = []
        e = c["elo"]
        if m.get("sport") == "table_tennis":
            out.append(f"Elo TT: {a} {e['elo_a']:.0f} vs {b} {e['elo_b']:.0f} → {_pct(comps['elo'])} para {a}.")
            if comps["ml"] is not None:
                out.append(f"Modelo ranking/forma: {_pct(comps['ml'])} para {a}.")
        else:
            out.append(f"Elo global {e['elo_a']:.0f} vs {e['elo_b']:.0f}; Elo en {c['surface'] or 'superficie n/d'} "
                       f"{e['surface_elo_a']:.0f} vs {e['surface_elo_b']:.0f} → {_pct(comps['elo'])} para {a}.")
            if comps["ml"] is not None:
                out.append(f"Modelo ML ({c['ml_kind']}) con Elo, ranking, forma, H2H y saque/resto: {_pct(comps['ml'])}.")
            if comps["monte_carlo"] is not None:
                out.append(f"Modelo de puntos (saque/resto históricos, Markov): {_pct(comps['monte_carlo'])}.")
            h = c.get("h2h") or {}
            if h.get("a") or h.get("b"):
                out.append(f"H2H: {a} {h['a']} - {h['b']} {b}.")
        if comps["experts"] is not None:
            out.append(f"Consenso de {experts.get('n')} experto(s): {_pct(comps['experts'])} para {a}.")
        out.append(f"Ensemble pre-partido (media ponderada en logit): {_pct(pre)}.")
        if live:
            sc = f"sets {st.sets_won[0]}-{st.sets_won[1]}" if m.get("sport") == "tennis" else \
                f"juegos {st.sets_won[0]}-{st.sets_won[1]}"
            extra = f", juego {st.games[0]}-{st.games[1]}" if m.get("sport") == "tennis" else ""
            out.append(f"En vivo ({sc}{extra}, puntos {st.points[0]}-{st.points[1]}): simulación punto a punto "
                       f"→ {_pct(final)} para {a}.")
        out.append("Probabilidades acotadas a [2%, 98%]. Estimación estadística, no una garantía.")
        return out


_ens: Ensemble | None = None


def get_ensemble() -> Ensemble:
    global _ens
    if _ens is None:
        _ens = Ensemble()
    return _ens

"""Value-bet maths: edge, implied / de-vigged probability, Kelly, CLV, confidence.

A positive model edge is an *estimate*; it does not guarantee profit. Models are
noisy and bookmakers are usually well calibrated, which is why large edges are
flagged as suspicious rather than celebrated."""
from __future__ import annotations

from dataclasses import dataclass


def implied_prob(odds: float) -> float:
    return 1.0 / odds if odds and odds > 1.0 else 1.0


def overround(odds_a: float, odds_b: float) -> float:
    return implied_prob(odds_a) + implied_prob(odds_b) - 1.0


def fair_probs(odds_a: float, odds_b: float) -> tuple[float, float]:
    """Proportional de-vig of a two-way market."""
    ia, ib = implied_prob(odds_a), implied_prob(odds_b)
    s = ia + ib
    return ia / s, ib / s


def edge(p: float, odds: float) -> float:
    """Expected value per unit staked: p * odds - 1."""
    return p * odds - 1.0


def kelly(p: float, odds: float) -> float:
    """Full Kelly fraction f* = (b p - q) / b with b = odds - 1. Never negative."""
    b = odds - 1.0
    if b <= 0:
        return 0.0
    return max(0.0, (b * p - (1.0 - p)) / b)


def stake(p: float, odds: float, bankroll: float, fraction: float = 0.5, max_stake_pct: float = 0.05) -> float:
    f = min(kelly(p, odds) * fraction, max_stake_pct)
    return round(max(0.0, f) * bankroll, 2)


def clv(entry_odds: float, closing_odds: float) -> float | None:
    """Closing-line value = entry / closing - 1 (positive = beat the close)."""
    if not entry_odds or not closing_odds or closing_odds <= 1.0:
        return None
    return entry_odds / closing_odds - 1.0


def min_edge_for(sport: str, settings: dict) -> float:
    return settings.get("min_edge_tt", 0.025) if sport == "table_tennis" else settings.get("min_edge_tennis", 0.015)


def is_suspicious(e: float, sport: str, settings: dict) -> bool:
    lim = settings.get("suspicious_edge", 0.08)
    if sport == "table_tennis":
        lim = lim * 1.5  # TT markets are thinner/noisier; flag at a higher level
    return e > lim


def confidence(model_probs: list[float], data_quality: float, suspicious: bool) -> tuple[str, float]:
    """Confidence from agreement between models (spread of their probabilities for
    the selection) and data quality (0-1). Returns (label, score)."""
    probs = [p for p in model_probs if p is not None]
    if len(probs) >= 2:
        spread = max(probs) - min(probs)
        agreement = max(0.0, 1.0 - spread / 0.25)
    else:
        agreement = 0.4
    score = 0.6 * agreement + 0.4 * max(0.0, min(1.0, data_quality))
    if suspicious:
        score *= 0.6
    score = round(max(0.0, min(1.0, score)), 3)
    label = "alta" if score >= 0.7 else "media" if score >= 0.45 else "baja"
    return label, score


@dataclass
class Evaluation:
    side: str
    odds: float
    model_prob: float
    implied_prob: float
    fair_prob: float
    edge: float
    kelly_full: float
    kelly_fraction: float
    stake: float
    suspicious: bool
    is_value: bool


def evaluate_side(side: str, p: float, odds: float, other_odds: float, sport: str, settings: dict) -> Evaluation:
    fa, fb = fair_probs(odds, other_odds) if other_odds else (implied_prob(odds), None)
    e = edge(p, odds)
    kf = kelly(p, odds)
    frac = settings.get("kelly_fraction", 0.5)
    st = stake(p, odds, settings.get("bankroll", 1000.0), frac, settings.get("max_stake_pct", 0.05))
    susp = is_suspicious(e, sport, settings)
    return Evaluation(side, odds, p, implied_prob(odds), fa, e, kf, round(kf * frac, 4), st, susp,
                      e > min_edge_for(sport, settings))

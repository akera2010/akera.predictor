import pytest

from akeraten import value_detector as vd
from akeraten.config import DEFAULT_SETTINGS


def test_edge_example():
    assert vd.edge(0.55, 2.10) == pytest.approx(0.155)


def test_implied_and_fair():
    assert vd.implied_prob(2.0) == pytest.approx(0.5)
    fa, fb = vd.fair_probs(1.85, 2.05)
    assert fa + fb == pytest.approx(1.0)
    assert fa > fb
    assert vd.overround(1.85, 2.05) == pytest.approx(1 / 1.85 + 1 / 2.05 - 1)


def test_kelly():
    # f* = (b p - q) / b with b = 1.10, p = .55
    assert vd.kelly(0.55, 2.10) == pytest.approx((1.1 * 0.55 - 0.45) / 1.1)
    assert vd.kelly(0.40, 2.0) == 0.0  # negative edge -> no bet
    assert vd.kelly(0.5, 1.0) == 0.0


def test_half_kelly_stake_and_cap():
    full = vd.kelly(0.55, 2.10)
    assert vd.stake(0.55, 2.10, 1000, 0.5, 1.0) == pytest.approx(round(full * 0.5 * 1000, 2))
    # cap at 5 % of bankroll
    assert vd.stake(0.9, 3.0, 1000, 1.0, 0.05) == pytest.approx(50.0)


def test_clv():
    assert vd.clv(2.10, 1.95) == pytest.approx(2.10 / 1.95 - 1)
    assert vd.clv(1.80, 2.00) < 0
    assert vd.clv(2.0, None) is None


def test_thresholds_by_sport():
    s = dict(DEFAULT_SETTINGS)
    # 2 % edge: value in tennis (1.5 %) but not in table tennis (2.5 %)
    p = 1.02 / 2.0
    assert vd.evaluate_side("a", p, 2.0, 1.9, "tennis", s).is_value
    assert not vd.evaluate_side("a", p, 2.0, 1.9, "table_tennis", s).is_value
    p = 1.03 / 2.0
    assert vd.evaluate_side("a", p, 2.0, 1.9, "table_tennis", s).is_value


def test_suspicious_flag():
    s = dict(DEFAULT_SETTINGS)
    assert vd.is_suspicious(0.09, "tennis", s)
    assert not vd.is_suspicious(0.05, "tennis", s)
    ev = vd.evaluate_side("a", 0.6, 2.0, 1.9, "tennis", s)  # edge 20 %
    assert ev.suspicious and ev.is_value


def test_confidence_levels():
    assert vd.confidence([0.6, 0.61, 0.6], 1.0, False)[0] == "alta"
    assert vd.confidence([0.4, 0.75], 0.3, False)[0] == "baja"
    lab, sc = vd.confidence([0.6, 0.61], 1.0, True)
    assert sc < vd.confidence([0.6, 0.61], 1.0, False)[1]
    assert 0 <= sc <= 1

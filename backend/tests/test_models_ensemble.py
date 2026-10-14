import pytest

from akeraten.models.ensemble import P_MAX, P_MIN, get_ensemble


def base(**kw):
    m = {"id": "t1", "sport": "tennis", "player_a": "Jannik Sinner", "player_b": "Pedro Martinez", "surface": "hard",
         "status": "upcoming", "best_of": 3, "rank_a": 2, "rank_b": 52, "category": "ATP", "score": {}}
    m.update(kw)
    return m


def test_probabilities_bounded_and_sensible():
    e = get_ensemble()
    r = e.predict(base())
    assert P_MIN <= r["prob_a"] <= P_MAX and r["prob_a"] + r["prob_b"] == pytest.approx(1.0)
    assert r["prob_a"] > 0.6  # clear favourite
    assert set(r["breakdown"]) >= {"elo", "ml", "monte_carlo", "experts"}
    assert r["explanation"]


def test_swap_players_is_roughly_symmetric():
    e = get_ensemble()
    p = e.predict(base())["prob_a"]
    q = e.predict(base(player_a="Pedro Martinez", player_b="Jannik Sinner", rank_a=52, rank_b=2))["prob_a"]
    assert p + q == pytest.approx(1.0, abs=0.02)


def test_live_score_moves_probability():
    e = get_ensemble()
    pre = e.predict(base())["prob_a"]
    losing = e.predict(base(status="live", score={"sets": [[2, 6], [1, 4]], "points": "0-40"}, server="a"))["prob_a"]
    assert losing < pre
    assert losing >= P_MIN


def test_extreme_clipped():
    e = get_ensemble()
    r = e.predict(base(status="live", score={"sets": [[6, 0], [5, 0]], "points": "40-0"}, server="a"))
    assert r["prob_a"] == pytest.approx(P_MAX)


def test_experts_shift_prematch():
    e = get_ensemble()
    m = base(player_a="Carlos Alcaraz", player_b="Jannik Sinner", rank_a=1, rank_b=2)
    p0 = e.predict(m)["prob_a"]
    p1 = e.predict(m, {"consensus_a": 0.8, "n": 4})["prob_a"]
    assert p1 > p0


def test_table_tennis_and_mc_breakdown():
    e = get_ensemble()
    m = {"id": "x", "sport": "table_tennis", "player_a": "Wang Chuqin", "player_b": "Alvaro Robles", "status": "live",
         "best_of": 5, "rank_a": 1, "rank_b": 40, "score": {"sets": [[11, 5], [3, 4]], "points": "3-4"}, "server": "a"}
    r = e.predict(m, iterations=10_000, seed=1)
    assert r["prob_a"] > 0.8
    mcb = r["breakdown"]["monte_carlo"]
    assert mcb["iterations"] == 10_000 and abs(sum(mcb["set_score_dist"].values()) - 1) < 1e-3

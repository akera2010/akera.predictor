import pytest

from akeraten.models import monte_carlo as mc


def test_equal_players_half():
    assert mc.prematch_prob_exact(0.64, 0.64, "tennis", 3) == pytest.approx(0.5, abs=1e-9)
    assert mc.prematch_prob_exact(0.53, 0.53, "table_tennis", 5) == pytest.approx(0.5, abs=1e-9)
    r = mc.simulate(0.64, 0.64, sport="tennis", best_of=3, iterations=10_000, seed=1)
    assert r["prob_a"] == pytest.approx(0.5, abs=0.02)
    r = mc.simulate(0.53, 0.53, sport="table_tennis", best_of=7, iterations=10_000, seed=2)
    assert r["prob_a"] == pytest.approx(0.5, abs=0.02)


def test_symmetry():
    p = mc.prematch_prob_exact(0.67, 0.62, "tennis", 5)
    q = mc.prematch_prob_exact(0.62, 0.67, "tennis", 5)
    assert p + q == pytest.approx(1.0, abs=1e-9)
    p = mc.prematch_prob_exact(0.55, 0.52, "table_tennis", 5)
    q = mc.prematch_prob_exact(0.52, 0.55, "table_tennis", 5)
    assert p + q == pytest.approx(1.0, abs=1e-9)


def test_stronger_player_and_best_of_amplifies():
    p3 = mc.prematch_prob_exact(0.66, 0.62, "tennis", 3)
    p5 = mc.prematch_prob_exact(0.66, 0.62, "tennis", 5)
    assert 0.5 < p3 < p5 < 1


def test_mc_matches_exact():
    st = mc.state_from_score("tennis", {"sets": [[6, 4], [3, 2]], "points": "30-15"}, "a", 3, "live")
    exact = mc.inplay_prob_exact(0.64, 0.62, st)
    sim = mc.simulate(0.64, 0.62, st, iterations=20_000, seed=3)
    assert sim["prob_a"] == pytest.approx(exact, abs=0.015)
    assert sum(sim["set_score_dist"].values()) == pytest.approx(1.0, abs=1e-3)
    assert exact > mc.prematch_prob_exact(0.64, 0.62, "tennis", 3)  # leading -> higher


def test_tiebreak_and_tt_inplay():
    st = mc.MatchState("tennis", 3, (1, 1), (6, 6), (6, 5), 0, True)
    assert mc.inplay_prob_exact(0.64, 0.64, st) > 0.5
    st = mc.state_from_score("table_tennis", {"sets": [[11, 8], [11, 9], [10, 3]]}, "b", 5, "live")
    assert st.sets_won == (2, 0) and st.points == (10, 3)
    assert mc.inplay_prob_exact(0.53, 0.53, st) > 0.95
    sim = mc.simulate(0.53, 0.53, st, iterations=5000, seed=1)
    assert set(sim["set_score_dist"]) <= {"3-0", "3-1", "3-2", "2-3"}


def test_serve_prob_calibration_roundtrip():
    for target in (0.2, 0.5, 0.73, 0.9):
        pa, pb = mc.serve_probs_for(target, "tennis", 3, "ATP")
        assert mc.prematch_prob_exact(pa, pb, "tennis", 3) == pytest.approx(target, abs=0.01)
        pa, pb = mc.serve_probs_for(target, "table_tennis", 7)
        assert mc.prematch_prob_exact(pa, pb, "table_tennis", 7) == pytest.approx(target, abs=0.01)


def test_points_parsing():
    assert mc.parse_points("AD-40", tennis=True) == (4, 3)
    assert mc.parse_points("40-AD", tennis=True) == (3, 4)
    assert mc.parse_points("5-3", tennis=True, tiebreak=True) == (5, 3)
    assert mc.parse_points(None, tennis=True) == (0, 0)

import pytest

from akeraten.models.tennis_elo import TennisElo, expected, rating_from_rank
from akeraten.models.tt_elo import TTElo


def test_expected_symmetry():
    assert expected(1600, 1500) + expected(1500, 1600) == pytest.approx(1.0)
    assert expected(1500, 1500) == pytest.approx(0.5)


def test_elo_update_moves_ratings():
    e = TennisElo()
    e.update("A Player", "B Player", "clay")
    a, b = e.players["A Player"], e.players["B Player"]
    assert a["elo"] > 1500 > b["elo"]
    assert a["clay"] > 1500 > b["clay"]
    assert a["hard"] == 1500  # other surfaces untouched
    assert a["elo"] - 1500 == pytest.approx(1500 - b["elo"])  # zero-sum with equal K


def test_k_factor_decays():
    e = TennisElo()
    for _ in range(30):
        e.update("Vet", "Opp")
    before = e.players["Vet"]["elo"]
    e.update("Vet", "Newbie")
    gain_vet = e.players["Vet"]["elo"] - before
    assert gain_vet < 250 / 5 ** 0.4 * 0.5  # much smaller than a newcomer's first-match K


def test_unknown_player_uses_rank():
    e = TennisElo()
    p = e.predict("Nobody One", "Nobody Two", "hard", rank_a=5, rank_b=300)
    assert p["prob_a"] > 0.8
    assert rating_from_rank(1) > rating_from_rank(100)


def test_trained_ratings_load():
    from akeraten.models.tennis_elo import get_tennis_elo

    e = get_tennis_elo()
    assert len(e.players) > 100
    assert e.resolve("Sinner J.") == "Jannik Sinner"


def test_tt_elo_seeded_and_update():
    t = TTElo()
    p = t.predict("Wang Chuqin", "Alvaro Robles")
    assert p["known_a"] and p["known_b"] and p["prob_a"] > 0.7
    r0 = t.rating("Alvaro Robles")[0]
    t.update("Alvaro Robles", "Wang Chuqin")
    assert t.rating("Alvaro Robles")[0] > r0

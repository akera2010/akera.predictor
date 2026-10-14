from akeraten.data_ingestion.demo import DemoProvider
from akeraten.engine import Engine
from akeraten.players import tennis_player_index, tt_player_index


def test_demo_provider_matches():
    d = DemoProvider(seed=4)
    ms = d.fetch()
    assert len(ms) >= 20
    sports = {m["sport"] for m in ms}
    assert sports == {"tennis", "table_tennis"}
    known = set(tennis_player_index()) | set(tt_player_index())
    for m in ms:
        assert m["source"] == "demo"
        assert m["player_a"] in known and m["player_b"] in known
        if m["odds"]:
            margin = 1 / m["odds"]["player_a"] + 1 / m["odds"]["player_b"] - 1
            assert 0.03 < margin < 0.09
    cats = {m["category"] for m in ms}
    assert {"ATP", "WTA", "WTT"} <= cats


def test_demo_points_progress():
    d = DemoProvider(seed=5, points_per_tick=1.0)
    live = [m for m in d.matches.values() if m.status == "live"]
    before = sum(sum(m.stats["points_won"]) for m in live)
    for _ in range(20):
        d.step()
    after = sum(sum(m.stats["points_won"]) for m in live)
    assert after > before


def test_engine_handful_of_value_bets():
    e = Engine(demo=True, seed=11, persist=False)
    counts = []
    for _ in range(30):
        snap = e.tick()
        counts.append(len(snap["value_bets"]))
    avg = sum(counts) / len(counts)
    assert 0 < avg <= 12, counts
    for b in snap["value_bets"]:
        assert b["edge"] > 0.015
        assert 0.02 <= b["model_prob"] <= 0.98
    st = e.stats()
    assert st["n_value_bets"] > 0 and st["bankroll_curve"]

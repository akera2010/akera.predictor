from akeraten.expert_tracker import ExpertTracker, load_experts
from akeraten.expert_tracker.nlp import extract_picks

MS = [{"id": "m1", "player_a": "Carlos Alcaraz", "player_b": "Jannik Sinner", "sport": "tennis"},
      {"id": "m2", "player_a": "Wang Chuqin", "player_b": "Hugo Calderano", "sport": "table_tennis"}]


def test_nlp_spanish_english_chinese():
    p = extract_picks("Alcaraz gana a Sinner hoy, pick seguro", MS)
    assert p[0]["side"] == "a" and p[0]["confidence"] > 0.7
    p = extract_picks("I think Sinner beats Alcaraz, maybe", MS)
    assert p[0]["side"] == "b" and p[0]["confidence"] < 0.6
    p = extract_picks("王楚钦 稳胜 卡尔德拉诺", MS)
    assert p[0]["match_id"] == "m2" and p[0]["side"] == "a"
    assert extract_picks("Sinner vs Alcaraz tomorrow", MS) == []
    assert extract_picks("Calderano 70% to win", MS)[0]["confidence"] == 0.7


def test_experts_seed_list():
    names = {e["name"] for e in load_experts()}
    for n in ("Benoît Maylin", "Boris Becker", "ProfeTenis", "Liu Guozheng", "Adam Bobrow", "VeloriumIQ",
              "DIVINE TIPS", "STATSCORE TipsterAPI"):
        assert n in names


def test_tracker_consensus_and_settle():
    t = ExpertTracker(demo=False, persist=False)
    m = dict(MS[0], odds={"player_a": 1.9, "player_b": 1.95})
    t.add_pick("Boris Becker", m, "a", 0.7, 1.9, store=False)
    t.add_pick("ProfeTenis", m, "a", 0.65, 1.9, store=False)
    assert t.add_pick("ProfeTenis", m, "b", 0.6, store=False) is None  # one pick per expert/match
    c = t.consensus("m1")
    assert c["n"] == 2 and c["consensus_a"] > 0.5
    t.on_match_live("m1", {"player_a": 1.8, "player_b": 2.05})
    t.settle("m1", "a")
    s = {e["name"]: e for e in t.summary()}
    assert s["Boris Becker"]["hit_rate"] == 1.0 and s["Boris Becker"]["clv"] > 0
    assert s["Boris Becker"]["recent"][0]["result"] == "win"


def test_demo_tracker_has_history():
    t = ExpertTracker(demo=True, seed=1, persist=False)
    s = t.summary()
    assert all(e["n_picks"] > 0 and e["hit_rate"] is not None for e in s)
    assert all(r["source"] == "demo" for e in s for r in e["recent"])

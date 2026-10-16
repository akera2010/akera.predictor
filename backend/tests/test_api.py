import pytest
from fastapi.testclient import TestClient

from akeraten.main import app

MATCH_KEYS = {"id", "sport", "match_id", "player_a", "player_b", "tournament", "surface", "status", "score", "odds",
              "timestamp", "source", "category", "start_time", "best_of", "server", "rank_a", "rank_b", "country_a",
              "country_b", "model_prob_a", "model_prob_b", "value_bet_count"}
VB_KEYS = {"id", "match_id", "sport", "tournament", "category", "player_a", "player_b", "status", "market", "selection",
           "selection_side", "odds", "bookmaker", "model_prob", "implied_prob", "fair_prob", "edge", "kelly_full",
           "kelly_fraction", "stake", "confidence", "confidence_score", "suspicious", "created_at", "models"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        for _ in range(3):
            c.app.state.engine.tick()
        yield c


def test_health(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["app"] == "AKERATEN v.0.1" and h["author"] == "Sandra Blanco (España | 2026)"
    assert h["mode"] == "demo" and h["disclaimer"]
    assert all({"name", "enabled", "status"} <= set(s) for s in h["sources"])


def test_matches_and_filters(client):
    ms = client.get("/api/matches").json()
    assert ms and all(MATCH_KEYS <= set(m) for m in ms)
    tt = client.get("/api/matches", params={"sport": "table_tennis", "status": "live"}).json()
    assert tt and all(m["sport"] == "table_tennis" and m["status"] == "live" for m in tt)
    t = ms[0]["tournament"]
    assert all(m["tournament"] == t for m in client.get("/api/matches", params={"tournament": t}).json())


def test_match_detail_and_predict(client):
    m = client.get("/api/matches", params={"status": "live"}).json()[0]
    d = client.get(f"/api/matches/{m['id']}").json()
    assert {"h2h", "stats", "prob_history", "form_a", "form_b"} <= set(d)
    assert {"a", "b", "last"} <= set(d["h2h"])
    assert d["prob_history"] and {"t", "model_a", "implied_a"} <= set(d["prob_history"][0])
    p = client.get(f"/api/predict/{m['id']}").json()
    assert {"match_id", "prob_a", "prob_b", "breakdown", "weights", "explanation"} <= set(p)
    assert p["breakdown"]["monte_carlo"]["iterations"] == 10_000
    assert {"prob_a", "iterations", "set_score_dist"} <= set(p["breakdown"]["monte_carlo"])
    assert {"consensus_a", "n"} <= set(p["breakdown"]["experts"])
    assert client.get("/api/matches/nope").status_code == 404
    assert client.get("/api/predict/nope").status_code == 404


def test_value_bets(client):
    vbs = client.get("/api/value-bets").json()
    edges = [v["edge"] for v in vbs]
    assert edges == sorted(edges, reverse=True)
    for v in vbs:
        assert VB_KEYS <= set(v)
        assert v["confidence"] in ("alta", "media", "baja") and v["market"] == "Ganador del partido"
        assert {"elo", "ml", "monte_carlo", "experts", "ensemble"} <= set(v["models"])
    hi = client.get("/api/value-bets", params={"min_edge": 0.05}).json()
    assert all(v["edge"] >= 0.05 for v in hi)
    assert all(v["sport"] == "tennis" for v in client.get("/api/value-bets", params={"sport": "tennis"}).json())


def test_experts_stats(client):
    ex = client.get("/api/experts").json()
    assert len(ex) >= 14
    assert {"name", "sport", "platform", "url", "weight", "hit_rate", "n_picks", "clv", "recent"} <= set(ex[0])
    st = client.get("/api/stats").json()
    assert {"n_value_bets", "avg_edge", "avg_clv", "clv_positive_pct", "roi_sim", "bankroll_curve", "by_sport",
            "hit_rate", "clv_values"} <= set(st)
    assert len(st["clv_values"]) <= 200 and all(isinstance(x, float) for x in st["clv_values"])
    assert st["bankroll_curve"] and {"t", "bankroll"} <= set(st["bankroll_curve"][0])


def test_settings_roundtrip(client):
    s = client.get("/api/settings").json()
    assert s["min_edge_tennis"] == 0.015 and s["min_edge_tt"] == 0.025 and s["suspicious_edge"] == 0.08
    r = client.put("/api/settings", json={"risk_profile": "conservador", "bankroll": 2500}).json()
    assert r["risk_profile"] == "conservador" and r["kelly_fraction"] == 0.25 and r["bankroll"] == 2500
    assert client.put("/api/settings", json={"risk_profile": "loco"}).status_code == 422
    client.put("/api/settings", json={"risk_profile": "moderado", "bankroll": 1000})


def test_websocket_snapshot(client):
    with client.websocket_connect("/ws/live") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "snapshot" and "matches" in msg["data"] and msg["ts"]


def test_root_serves_web_or_info(client):
    from akeraten.config import web_dir

    r = client.get("/")
    assert r.status_code == 200
    if (web_dir() / "index.html").exists():
        assert "text/html" in r.headers["content-type"]

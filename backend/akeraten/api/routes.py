"""REST API (contract shared with the web dashboard and the Android app)."""
from __future__ import annotations

import hmac
import json

from fastapi import APIRouter, Body, Header, HTTPException, Query, Request

from ..cache import get_cache
from ..config import APP_NAME, AUTHOR, DATA_DIR, DISCLAIMER, database_url, env, tick_seconds
from ..models.tennis_xgboost import get_tennis_ml

router = APIRouter(prefix="/api")


def _engine(request: Request):
    return request.app.state.engine


def _model_info() -> dict:
    info = {"ml": get_tennis_ml().name}
    p = DATA_DIR / "model_metrics.json"
    if p.exists():
        try:
            m = json.loads(p.read_text())
            sel = m.get("selected_model")
            info.update({"trained_on": m.get("source"), "test_year": m.get("test_year"),
                         "test_metrics": (m.get("results", {}).get(sel) or {}).get("test"),
                         "elo_baseline_test": (m.get("results", {}).get("elo_baseline") or {}).get("test")})
        except json.JSONDecodeError:
            pass
    return info


@router.get("/health")
def health(request: Request):
    e = _engine(request)
    return {"status": "ok", "app": APP_NAME, "author": AUTHOR, "mode": "demo" if e.demo else "live",
            "sources": e.sources(), "disclaimer": DISCLAIMER, "responsible_gambling": DISCLAIMER,
            "tick_seconds": tick_seconds(), "last_tick": e.last_tick, "tick_ms": e.last_tick_ms,
            "n_matches": len(e.snapshot["matches"]), "n_value_bets": len(e.snapshot["value_bets"]),
            "models": _model_info(), "cache": get_cache().backend,
            "database": database_url().split(":", 1)[0]}


@router.get("/connect")
def connect_info():
    """Addresses at which phones on the same Wi-Fi can reach this backend."""
    from ..discovery import DISCOVERY_PORT, beacon
    return {**beacon(), "discovery_udp_port": DISCOVERY_PORT}


@router.get("/matches")
def matches(request: Request, sport: str | None = None, status: str | None = None, tournament: str | None = None,
            category: str | None = None):
    out = _engine(request).snapshot["matches"]
    if sport:
        out = [m for m in out if m["sport"] == sport]
    if status:
        out = [m for m in out if m["status"] == status]
    if tournament:
        t = tournament.lower()
        out = [m for m in out if t in (m.get("tournament") or "").lower()]
    if category:
        out = [m for m in out if (m.get("category") or "").lower() == category.lower()]
    return out


@router.get("/matches/{match_id}")
def match_detail(request: Request, match_id: str):
    d = _engine(request).match_detail(match_id)
    if d is None:
        raise HTTPException(404, f"match {match_id} not found")
    return d


@router.get("/value-bets")
def value_bets(request: Request, sport: str | None = None, min_edge: float | None = Query(None, ge=-1, le=10)):
    return _engine(request).value_bets(sport or None, min_edge)


@router.get("/predict/{match_id}")
def predict(request: Request, match_id: str, iterations: int = Query(10_000, ge=500, le=100_000)):
    d = _engine(request).predict_detail(match_id, iterations)
    if d is None:
        raise HTTPException(404, f"match {match_id} not found")
    return d


@router.get("/experts")
def experts(request: Request):
    return _engine(request).tracker.summary()


@router.post("/experts/webhook/discord")
def discord_webhook(request: Request, payload: dict = Body(...), x_webhook_secret: str | None = Header(None)):
    secret = env("DISCORD_WEBHOOK_SECRET")
    if secret and not hmac.compare_digest(secret, x_webhook_secret or ""):
        raise HTTPException(401, "bad webhook secret")
    e = _engine(request)
    msg = e.tracker.ingest_discord(payload)
    n = e.tracker.poll_sources(list(e.matches.values())) if not e.demo else 0
    return {"accepted": True, "message": msg, "new_picks": n}


@router.get("/stats")
def stats(request: Request):
    return _engine(request).stats()


@router.get("/alerts")
def alerts(request: Request, limit: int = Query(50, ge=1, le=100)):
    return list(_engine(request).alerts)[-limit:][::-1]


@router.get("/settings")
def get_settings(request: Request):
    return dict(_engine(request).settings)


@router.put("/settings")
def put_settings(request: Request, patch: dict = Body(...)):
    try:
        return _engine(request).update_settings(patch)
    except (ValueError, TypeError) as ex:
        raise HTTPException(422, str(ex)) from ex

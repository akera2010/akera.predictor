"""APScheduler jobs:
  * ingest + models + value detection : every TICK_SECONDS (3 s demo / 30 s live)
  * experts (poll sources)            : every 5 min
  * model artifacts refresh           : every 5 min (reloads ratings/ML if retrained)
  * closing-line capture              : every 60 s
  * DB cleanup                        : every 6 h
Value detection runs inside every ingest tick; alerts go to WebSocket + Telegram."""
from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..config import tick_seconds

log = logging.getLogger("akeraten.scheduler")


async def run_tick(engine, broadcaster) -> None:
    try:
        snap = await asyncio.to_thread(engine.tick)
    except Exception as e:  # noqa: BLE001
        log.exception("tick failed: %s", e)
        return
    await broadcaster.send("matches", snap["matches"])
    await broadcaster.send("value_bets", snap["value_bets"])
    for a in engine.pending_alerts:
        await broadcaster.send("alert", a)


async def run_experts(engine) -> None:
    if engine.demo:
        return
    try:
        n = await asyncio.to_thread(engine.tracker.poll_sources, list(engine.matches.values()))
        log.info("experts: %d new picks", n)
    except Exception as e:  # noqa: BLE001
        log.warning("expert polling failed: %s", e)


async def refresh_models() -> None:
    from ..models import tennis_elo, tennis_xgboost

    def _reload():
        new_elo = tennis_elo.TennisElo.load()
        if new_elo.players:
            tennis_elo._elo = new_elo
        tennis_xgboost._ml = tennis_xgboost.TennisML()
    try:
        await asyncio.to_thread(_reload)
    except Exception as e:  # noqa: BLE001
        log.warning("model refresh failed: %s", e)


def start_scheduler(engine, broadcaster) -> AsyncIOScheduler:
    sch = AsyncIOScheduler(timezone="UTC")
    common = {"max_instances": 1, "coalesce": True, "misfire_grace_time": 30}
    sch.add_job(run_tick, "interval", seconds=tick_seconds(), args=[engine, broadcaster], id="ingest", **common)
    sch.add_job(run_experts, "interval", minutes=5, args=[engine], id="experts", **common)
    sch.add_job(refresh_models, "interval", minutes=5, id="models", **common)
    sch.add_job(engine.capture_due_closing_lines, "interval", seconds=60, id="closing_line", **common)
    sch.add_job(engine.cleanup_db, "interval", hours=6, id="db_cleanup", **common)
    sch.start()
    return sch

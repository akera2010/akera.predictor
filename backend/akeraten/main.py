"""AKERATEN v.0.1 - FastAPI application.

Run:  cd backend && uvicorn akeraten.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .api.ws import Broadcaster, message
from .config import APP_NAME, AUTHOR, DISCLAIMER, env_bool, web_dir
from .db import init_db
from .discovery import Beacon
from .engine import Engine
from .scheduler.jobs import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("akeraten")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    engine = Engine()
    await asyncio.to_thread(engine.tick)  # first snapshot before serving
    app.state.engine = engine
    app.state.broadcaster = Broadcaster()
    sch = None
    if not env_bool("AKERATEN_DISABLE_SCHEDULER"):
        sch = start_scheduler(engine, app.state.broadcaster)
    beacon = Beacon().start()  # lets the Android app find this PC on the LAN
    log.info("%s started in %s mode", APP_NAME, "DEMO" if engine.demo else "LIVE")
    yield
    beacon.stop()
    if sch:
        sch.shutdown(wait=False)


app = FastAPI(title=APP_NAME, version="0.1.0", lifespan=lifespan,
              description=f"{APP_NAME} · {AUTHOR}. Monitor de value bets de tenis y tenis de mesa. {DISCLAIMER}")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    b: Broadcaster = ws.app.state.broadcaster
    e: Engine = ws.app.state.engine
    await b.connect(ws)
    try:
        await ws.send_text(message(
            "snapshot", {"matches": e.snapshot["matches"], "value_bets": e.snapshot["value_bets"],
                         "mode": "demo" if e.demo else "live"}))
        while True:  # keep the socket open; clients may send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        await b.disconnect(ws)


_web = web_dir()
if _web.is_dir():
    app.mount("/", StaticFiles(directory=str(_web), html=True), name="web")
else:
    @app.get("/")
    def root():
        return {"app": APP_NAME, "author": AUTHOR, "docs": "/docs", "health": "/api/health",
                "note": "web/ dashboard not found; API only"}

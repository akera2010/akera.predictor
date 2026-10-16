"""WebSocket fan-out for /ws/live."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import WebSocket

log = logging.getLogger("akeraten.ws")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def message(kind: str, data) -> str:
    return json.dumps({"type": kind, "data": data, "ts": _ts()}, default=lambda o: float(o) if hasattr(o, "__float__") else str(o),
                      ensure_ascii=False)


class Broadcaster:
    def __init__(self):
        self.clients: set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self.lock:
            self.clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self.lock:
            self.clients.discard(ws)

    async def send(self, kind: str, data) -> None:
        if not self.clients:
            return
        msg = message(kind, data)
        async with self.lock:
            clients = list(self.clients)
        dead = []
        for ws in clients:
            try:
                await asyncio.wait_for(ws.send_text(msg), timeout=5)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        if dead:
            async with self.lock:
                for ws in dead:
                    self.clients.discard(ws)

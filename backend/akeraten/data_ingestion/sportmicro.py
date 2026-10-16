"""SportMicro via RapidAPI (tennis + table tennis live events, SofaScore-like format).
Host configurable with SPORTMICRO_HOST; key RAPIDAPI_KEY."""
from __future__ import annotations

from ..config import env
from .base import BaseClient
from .sofascore_format import sofascore_event


class SportMicroClient(BaseClient):
    name = "sportmicro"
    sports = ("tennis", "table_tennis")
    env_keys = ("RAPIDAPI_KEY",)
    rate_limit_per_min = 20

    def fetch_raw(self) -> list:
        host = env("SPORTMICRO_HOST", "sportmicro.p.rapidapi.com")
        h = {"X-RapidAPI-Key": self.key(), "X-RapidAPI-Host": host}
        out = []
        for sport in ("tennis", "table-tennis"):
            body = self.request("GET", f"https://{host}/api/v1/{sport}/events/live", headers=h)
            out += (body.get("events") or body.get("data") or []) if isinstance(body, dict) else []
        return out

    def normalize(self, it: dict) -> dict | None:
        return sofascore_event(it, self.name, "smicro")

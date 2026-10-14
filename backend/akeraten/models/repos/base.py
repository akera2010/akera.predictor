"""Wrapper interface for third-party prediction repositories.

The external repos are NOT vendored. `scripts/clone_repos.sh` clones them into
backend/external_repos/<name>. Each repo has its own data/feature pipeline, so
integration is done through an optional adapter file you write once:

    backend/external_repos/<name>/akeraten_adapter.py
        def predict_match(player_a, player_b, surface, tournament) -> float | None

If the repo (or its adapter) is absent, predict_match() returns None and the
ensemble simply ignores it. Weights in extra_repos.json default to 0.0 (off)."""
from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

import httpx

from ...config import BACKEND_DIR, env

log = logging.getLogger("akeraten.repos")
REPOS_DIR = BACKEND_DIR / "external_repos"


class RepoWrapper:
    def __init__(self, spec: dict):
        self.spec = spec
        self.name = spec["name"]
        self.sport = spec.get("sport", "tennis")
        self.weight = float(spec.get("weight", 0.0))
        self.path = REPOS_DIR / self.name
        self._fn = None
        self._loaded = False

    @property
    def available(self) -> bool:
        return (self.path / "akeraten_adapter.py").exists()

    def _load(self):
        if self._loaded:
            return self._fn
        self._loaded = True
        adapter = self.path / "akeraten_adapter.py"
        if not adapter.exists():
            return None
        try:
            spec = importlib.util.spec_from_file_location(f"akeraten_ext_{self.name.replace('-', '_')}", adapter)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            self._fn = getattr(mod, "predict_match", None)
        except Exception as e:  # noqa: BLE001
            log.warning("adapter for %s failed to load: %s", self.name, e)
        return self._fn

    def predict_match(self, player_a: str, player_b: str, surface: str | None = None,
                      tournament: str | None = None) -> float | None:
        fn = self._load()
        if fn is None:
            return None
        try:
            p = fn(player_a, player_b, surface, tournament)
            return None if p is None else min(0.99, max(0.01, float(p)))
        except Exception as e:  # noqa: BLE001
            log.debug("%s predict failed: %s", self.name, e)
            return None

    def info(self) -> dict:
        return {"name": self.name, "repo": self.spec.get("repo"), "sport": self.sport, "available": self.available,
                "weight": self.weight, "note": self.spec.get("note")}


class HttpRepoWrapper(RepoWrapper):
    """For repos exposed as an HTTP service (e.g. a Hugging Face Space). ASSUMED
    contract: POST {url}/predict {"player_a","player_b","surface","tournament"} ->
    {"prob_a": float}. Adapt if the service differs."""

    @property
    def url(self) -> str | None:
        return env(self.spec.get("env_url", ""))

    @property
    def available(self) -> bool:
        return bool(self.url)

    def predict_match(self, player_a, player_b, surface=None, tournament=None):
        if not self.url:
            return None
        try:
            r = httpx.post(self.url.rstrip("/") + "/predict", timeout=8,
                           json={"player_a": player_a, "player_b": player_b, "surface": surface,
                                 "tournament": tournament})
            r.raise_for_status()
            p = r.json().get("prob_a")
            return None if p is None else min(0.99, max(0.01, float(p)))
        except Exception as e:  # noqa: BLE001
            log.debug("%s http predict failed: %s", self.name, e)
            return None

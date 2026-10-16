"""External model repositories (optional). See base.py."""
from __future__ import annotations

import json
from pathlib import Path

from .base import REPOS_DIR, HttpRepoWrapper, RepoWrapper

SPEC_PATH = Path(__file__).resolve().parent.parent / "extra_repos.json"


def load_repo_wrappers(path: Path = SPEC_PATH) -> list[RepoWrapper]:
    try:
        specs = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return []
    return [HttpRepoWrapper(s) if s.get("kind") == "http" else RepoWrapper(s) for s in specs if s.get("name")]


def predict_external(player_a: str, player_b: str, surface: str | None, tournament: str | None,
                     sport: str = "tennis") -> dict[str, float | None]:
    return {w.name: w.predict_match(player_a, player_b, surface, tournament)
            for w in load_repo_wrappers() if w.sport == sport}


__all__ = ["RepoWrapper", "HttpRepoWrapper", "load_repo_wrappers", "predict_external", "REPOS_DIR"]

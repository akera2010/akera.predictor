"""Central configuration for AKERATEN. All secrets come from environment variables
(optionally loaded from a .env file). Nothing secret is ever hard-coded here."""
from __future__ import annotations

import os
from pathlib import Path

try:  # python-dotenv is optional at runtime
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

if load_dotenv is not None:
    load_dotenv(REPO_DIR / ".env", override=False)
    load_dotenv(BACKEND_DIR / ".env", override=False)

APP_NAME = "AKERATEN v.0.1"
AUTHOR = "Sandra Blanco (España | 2026)"
DISCLAIMER = (
    "Herramienta de análisis estadístico. No garantiza beneficios: las apuestas "
    "implican riesgo de pérdida. Juega con responsabilidad, solo mayores de 18 años. "
    "Ayuda: jugarbien.es | 900 200 225. / Statistical analysis tool only; no profit "
    "is guaranteed. Gamble responsibly (18+)."
)


def env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on", "si", "sí")


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


DATA_DIR = Path(env("AKERATEN_DATA_DIR", str(BACKEND_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Keys whose presence means "real match/odds data is available".
DATA_SOURCE_KEYS = [
    "LIVETENNISAPI_KEY", "SPORTRADAR_TT_KEY", "APIFY_TOKEN", "RAPIDAPI_KEY",
    "SPORTAPI_KEY", "ODDS_API_KEY", "BETFAIR_APP_KEY",
]


def demo_mode() -> bool:
    """DEMO_MODE=true forces the simulator; DEMO_MODE=false forces live APIs.
    Unset -> demo only if no data-source key is configured."""
    v = os.getenv("DEMO_MODE")
    if v not in (None, ""):
        return env_bool("DEMO_MODE")
    return not any(env(k) for k in DATA_SOURCE_KEYS)


def database_url() -> str:
    return env("DATABASE_URL", f"sqlite:///{DATA_DIR / 'akeraten.db'}")


def tick_seconds() -> float:
    return env_float("TICK_SECONDS", 3.0 if demo_mode() else 30.0)


def web_dir() -> Path:
    return Path(env("WEB_DIR", str(REPO_DIR / "web")))


DEFAULT_SETTINGS = {
    "bankroll": 1000.0,
    "kelly_fraction": 0.5,
    "min_edge_tennis": 0.015,
    "min_edge_tt": 0.025,
    "suspicious_edge": 0.08,
    "risk_profile": "moderado",
    "max_stake_pct": 0.05,
    "sports": ["tennis", "table_tennis"],
}

RISK_PROFILES = {
    "conservador": {"kelly_fraction": 0.25, "max_stake_pct": 0.02},
    "moderado": {"kelly_fraction": 0.5, "max_stake_pct": 0.05},
    "agresivo": {"kelly_fraction": 0.75, "max_stake_pct": 0.08},
}

TELEGRAM_MIN_EDGE = env_float("TELEGRAM_MIN_EDGE", 0.05)

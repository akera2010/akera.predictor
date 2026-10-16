"""Tennis ML model (gradient boosting / logistic regression) on Elo-derived features.

Training lives in scripts/train_models.py; this module defines the feature vector
(shared by training and inference) and loads the joblib artifact.
xgboost is optional: if it is not installed, sklearn models are used instead."""
from __future__ import annotations

import math
from pathlib import Path

from ..config import DATA_DIR

try:  # optional dependency
    import xgboost  # type: ignore # noqa: F401
    HAS_XGBOOST = True
except Exception:  # pragma: no cover
    HAS_XGBOOST = False

MODEL_PATH = DATA_DIR / "tennis_ml.joblib"

FEATURES = ["elo_diff", "surface_elo_diff", "log_rank_ratio", "form_diff", "h2h_diff",
            "fatigue_diff", "serve_diff", "return_diff", "bo5_elo_diff"]


def _log_rank(r) -> float:
    try:
        r = float(r)
        return math.log(r) if r > 0 else math.log(300)
    except (TypeError, ValueError):
        return math.log(300)


def build_features(pa: dict, pb: dict, surface: str | None, best_of: int = 3,
                   h2h_a: int = 0, h2h_b: int = 0, fatigue_a: float = 0, fatigue_b: float = 0) -> list[float]:
    """pa/pb: player dicts with elo, <surface> elo, rank, form (list of 1/0),
    serve (serve points won %), ret (return points won %)."""
    s = surface if surface in ("hard", "clay", "grass") else "hard"
    ea, eb = pa.get("elo", 1500), pb.get("elo", 1500)
    sa, sb = pa.get(s, ea), pb.get(s, eb)
    fa = pa.get("form") or []
    fb = pb.get("form") or []
    form_a = (sum(1 for x in fa if x in (1, "W")) + 2.5) / (len(fa) + 5)
    form_b = (sum(1 for x in fb if x in (1, "W")) + 2.5) / (len(fb) + 5)
    return [
        (ea - eb) / 100.0,
        (sa - sb) / 100.0,
        _log_rank(pb.get("rank")) - _log_rank(pa.get("rank")),
        form_a - form_b,
        max(-5, min(5, h2h_a - h2h_b)),
        float(fatigue_a - fatigue_b),
        (pa.get("serve") or 0.62) - (pb.get("serve") or 0.62),
        (pa.get("ret") or 0.38) - (pb.get("ret") or 0.38),
        (ea - eb) / 100.0 * (1.0 if best_of == 5 else 0.0),
    ]


class TennisML:
    def __init__(self, path: Path | str = MODEL_PATH):
        self.artifact = None
        p = Path(path)
        if p.exists():
            try:
                import joblib

                self.artifact = joblib.load(p)
            except Exception:  # pragma: no cover - corrupt / incompatible artifact
                self.artifact = None

    @property
    def available(self) -> bool:
        return self.artifact is not None

    @property
    def name(self) -> str:
        return self.artifact.get("kind", "none") if self.artifact else "none"

    def predict_features(self, xa: list[float], xb: list[float]) -> float | None:
        """Symmetrised: average of P(a beats b) and 1 - P(b beats a)."""
        if not self.artifact:
            return None
        m = self.artifact["model"]
        p1 = float(m.predict_proba([xa])[0][1])
        p2 = float(m.predict_proba([xb])[0][1])
        return 0.5 * (p1 + (1 - p2))

    def predict(self, pa: dict, pb: dict, surface: str | None, best_of: int = 3, h2h: dict | None = None) -> float | None:
        h2h = h2h or {"a": 0, "b": 0}
        xa = build_features(pa, pb, surface, best_of, h2h.get("a", 0), h2h.get("b", 0))
        xb = build_features(pb, pa, surface, best_of, h2h.get("b", 0), h2h.get("a", 0))
        return self.predict_features(xa, xb)


_ml: TennisML | None = None


def get_tennis_ml() -> TennisML:
    global _ml
    if _ml is None:
        _ml = TennisML()
    return _ml

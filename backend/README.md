# AKERATEN v.0.1 — backend

*Sandra Blanco (España | 2026)* · Monitor de value bets de tenis y tenis de mesa.

> **Aviso:** herramienta de análisis estadístico. **No garantiza beneficios**; apostar implica riesgo
> de pérdida. Solo mayores de 18 años. Juega con responsabilidad (jugarbien.es · 900 200 225).

## Quick start

```bash
cd backend
pip install -r requirements.txt
uvicorn akeraten.main:app --host 0.0.0.0 --port 8000      # http://localhost:8000  (docs: /docs)
python -m pytest -q                                       # tests
python scripts/train_models.py                            # (re)train Elo + ML artifacts into data/
```

With no API key in the environment the app runs in **DEMO mode**: a point-level simulator
(`akeraten/data_ingestion/demo.py`) generates live/upcoming ATP, WTA, Challenger, ITF, WTT, ITTF,
Setka Cup, TT Elite Series and Czech Liga Pro matches with real tour players (league rosters are
fictional), bookmaker odds with a 5–7 % margin, and simulated expert picks. Everything simulated is
tagged `"source": "demo"`. In demo mode the hidden “truth” is anchored on the model's own estimate plus
noise, so demo ROI/CLV show how the pipeline works, **not** how good the model is in reality.

Docker: `cp .env.example .env && docker compose up --build` (repo root; backend + Redis + Postgres).

## Layout

```
akeraten/
  main.py              FastAPI app (REST + /ws/live + static web/ at "/")
  engine.py            ingest → experts → models → value detection → DB → snapshot
  config.py cache.py   env settings; Redis (REDIS_URL) or in-memory TTL cache
  data_ingestion/      livetennisapi, sportradar_tt, apify_flashscore_tt, apify_sofascore, sportmicro,
                       sportapi_net, the_odds_api, betfair, extra_apis(.json), demo, schema, merge
  expert_tracker/      experts.json, extra_experts.json, sources (X v2, Weibo, Instagram, web, API, Discord
                       webhook-in), nlp (es/en/fr/zh), tracker (consensus, hit-rate, CLV)
  models/              tennis_elo, tennis_xgboost (GB/LR), tt_elo, monte_carlo, ensemble, repos/ + extra_repos.json
  value_detector/      edge, de-vig, Kelly/half-Kelly, stake cap, CLV, confidence, suspicious flag
  db/                  SQLAlchemy: matches, odds_snapshots, predictions, expert_predictions, value_bets, settings
  scheduler/           APScheduler jobs + Telegram alerts
scripts/train_models.py  scripts/synthetic_tennis.py  scripts/clone_repos.sh
data/                  tennis_ratings.json, tennis_ml.joblib, model_metrics.json (trained artifacts)
```

## Models

* **Elo** (surface-aware, FiveThirtyEight-style K) trained on Jeff Sackmann's `tennis_atp`/`tennis_wta`
  CSVs (2015–2024). If those cannot be downloaded the script falls back to a **synthetic** dataset and
  marks the artifacts `source: synthetic` (see `data/model_metrics.json`) — re-run it with network
  access to get real ratings.
* **ML**: logistic regression vs gradient boosting (xgboost if installed) on Elo diff, surface-Elo diff,
  log-rank ratio, form-10, H2H, fatigue, serve/return points won; selection on 2023, test on 2024.
* **Monte Carlo / Markov**: exact point-level DP + vectorised 10k-iteration simulation from any score
  (tennis Bo3/Bo5 with tie-breaks; table tennis Bo5/Bo7 to 11).
* **Ensemble**: logit-weighted Elo + ML + stats Markov + expert consensus pre-match; in play the
  pre-match strength drives the point model from the current score. Clipped to [2 %, 98 %].

## Notes

* Third-party payload shapes for LiveTennisAPI, SportAPI, Apify actors and SportMicro are **assumed**
  (documented at the top of each client) — verify against your plan's docs.
* Expert handles/URLs in `experts.json` should be verified; web/Weibo scraping is off by default
  (`ENABLE_WEB_SCRAPING`, `ENABLE_WEIBO_SCRAPING`) — respect each site's ToS/robots.txt.
* `.mcp.json` package names are placeholders for the listed MCP servers; adjust to the published names.

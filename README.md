# AirPulse — All 12 System Features (Section 2 of the plan)

Working implementations of all twelve system features from the AirPulse plan, wired into one FastAPI app (`main.py`) so the frontend team can integrate immediately.

- **Feature 1 — Hyperlocal AQI Prediction** (`agents/prediction_agent.py`): LightGBM regressor forecasting AQI 24/48/72 hours ahead per ward, with widening confidence intervals for longer horizons.
- **Feature 2 — Pollution Source Attribution** (`agents/attribution_agent.py`): RandomForest classifier attributing hotspots to traffic/construction/industrial/dust/stubble-burning with confidence + evidence.
- **Feature 3 — AI Intervention Recommendation Engine** (`agents/recommendation_agent.py`): Deterministic source × severity decision matrix producing role-specific, time-bound actions (deliberately rule-based, not LLM-driven, for auditability).
- **Feature 4 — Smart Enforcement Prioritization** (`agents/enforcement_agent.py`): Ranks registered emission sources by a composite risk score (proximity to hotspot, permit status, inspection recency, forecast severity).
- **Feature 5 — Citizen Health Advisory** (`agents/advisory_agent.py`): Personalized, multilingual (English + Hindi, easily extendable) health advisories based on forecast AQI + vulnerability profile.
- **Feature 6 — Geospatial Heatmaps** (`agents/heatmap_agent.py`): IDW interpolation of station readings onto a city grid for the map's heatmap layer.
- **Feature 7 — Trend Analysis** (`agents/trend_agent.py`): Weekday/weekend deltas, monthly seasonality, festival-linked spikes, and statistical anomaly days.
- **Feature 8 — AI Chat Assistant** (`agents/chat_agent.py`): TF-IDF retrieval over a curated knowledge corpus (`data/knowledge_corpus.py`) with citation-backed, optionally live-context-grounded answers ("why is AQI high near me today?"). A deliberately lighter-weight stand-in for the plan's Sentence-Transformers + RAG design — see the module docstring for the swap path to a real embedding model / LLM synthesis call.
- **Feature 9 — Real-time Alerts** (`agents/alert_agent.py`): Turns a risk-band advisory or an Emergency Detection trigger into a channel-appropriate (push/SMS/app feed) dispatch, with risk-based auto-escalation and a mock notification gateway (real Twilio/FCM integration only touches `_send()`).
- **Feature 10 — Multi-city Comparison** (`agents/comparison_agent.py`): Benchmarks cities on average AQI, intervention count, and average AQI drop per intervention.
- **Feature 11 — Emergency Pollution Detection** (`agents/emergency_agent.py`): Real-time rate-of-change + absolute-threshold + rolling z-score detection on sub-hourly readings.
- **Feature 12 — Analytics Dashboard** (`agents/analytics_agent.py`): Rolls up enforcement queue status, intervention outcome ROI over time, and hotspot source trends — the Admin Panel's closed-feedback-loop "wow" screen from Section 1/11 of the plan.

## Setup

```bash
pip install -r requirements.txt
```

## Run each agent standalone (prints a demo result)

```bash
python3 agents/attribution_agent.py
python3 agents/advisory_agent.py
python3 agents/trend_agent.py
python3 agents/prediction_agent.py
python3 agents/recommendation_agent.py
python3 agents/enforcement_agent.py
python3 agents/emergency_agent.py
python3 agents/chat_agent.py
python3 agents/alert_agent.py
python3 agents/analytics_agent.py
python3 agents/comparison_agent.py
python3 agents/heatmap_agent.py
```

## Run the API

```bash
uvicorn main:app --reload --port 8000
```

Then open `http://localhost:8000/docs` for interactive Swagger docs, or:

```bash
# Feature 1 — forecast
curl "http://localhost:8000/api/forecast/Ward-1?horizon_hr=48"
curl "http://localhost:8000/api/forecast/Ward-2/multi-horizon"

# Feature 2 — attribution
curl -X POST http://localhost:8000/api/attribution \
  -H "Content-Type: application/json" \
  -d '{"ward":"Ward-3","traffic_density_idx":0.2,"construction_permit_density":0.05,"industrial_stack_count":5,"thermal_anomaly_count":0,"dust_landuse_pct":0.05,"pm25":95}'

# Feature 3 — recommendations (manual or auto-piped from attribution+forecast)
curl -X POST http://localhost:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"ward":"Ward-3","source":"industrial","forecast_aqi":420}'
curl "http://localhost:8000/api/recommendations/Ward-1"

# Feature 4 — enforcement queue
curl "http://localhost:8000/api/enforcement/queue?top_n=5"

# Feature 5 — advisory
curl -X POST http://localhost:8000/api/advisory \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u9","ward":"Ward-2","language":"hi","conditions":["asthma"],"forecast_aqi":320}'

# Feature 6 — heatmap
curl "http://localhost:8000/api/heatmap/Lucknow?pollutant=aqi&resolution=40"

# Feature 7 — trends
curl http://localhost:8000/api/trends/Ward-4
curl http://localhost:8000/api/trends

# Feature 8 — chat assistant
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"how does the enforcement queue decide priority?"}'
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"why is my air quality bad today","ward":"Ward-3"}'

# Feature 9 — real-time alerts
curl -X POST http://localhost:8000/api/alerts/dispatch \
  -H "Content-Type: application/json" \
  -d '{"ward":"Ward-6","risk_level":"severe","message":"Air quality is severe in Ward-6. Stay indoors."}'
curl "http://localhost:8000/api/alerts/feed?limit=10"

# Feature 10 — multi-city comparison
curl "http://localhost:8000/api/compare?cities=Lucknow,Delhi&days=30"

# Feature 11 — emergency detection
curl "http://localhost:8000/api/emergency/check/Ward-5?simulate_spike=true"
curl "http://localhost:8000/api/emergency/check-all"

# Feature 12 — analytics dashboard
curl "http://localhost:8000/api/analytics/summary"
curl "http://localhost:8000/api/analytics/summary?city=Lucknow"
```

## Connecting to Neon (real database)

Your live Neon schema already exists (`db/migrations/001_init_schema.sql` mirrors it — **don't re-run 001, it's reference only**). Two additive migrations layer on top of it without touching existing data:

- `002_add_attribution_and_citizens.sql` — adds attribution raw-feature columns to `hotspots` and a `citizens` table for personalized advisories (Features 2 & 5).
- `003_add_alerts_log.sql` — adds the `alerts_log` table that `db/repository.py`'s `insert_alert_log()`/`fetch_recent_alerts()` require (Feature 9).

1. Copy `.env.example` to `.env` and paste your Neon **pooled** connection string (Neon Console → your project → Connection Details). Keep `sslmode=require`.
2. Load it:
   ```bash
   export $(cat .env | xargs)
   ```
3. Run both additive migrations (psql, or the Python fallback if psql isn't installed):
   ```bash
   psql "$DATABASE_URL" -f db/migrations/002_add_attribution_and_citizens.sql
   psql "$DATABASE_URL" -f db/migrations/003_add_alerts_log.sql
   # or, if psql isn't available (e.g. plain Git Bash on Windows):
   python db/run_migration.py db/migrations/002_add_attribution_and_citizens.sql
   python db/run_migration.py db/migrations/003_add_alerts_log.sql
   ```
4. Seed at least one row in `citizens` so `/api/advisory` has someone real to look up (or keep passing profile fields directly in the request, which works without the table too).
5. Start the API — it auto-detects `DATABASE_URL` and switches from mock to real data for trends/advisories/alerts/analytics, and writes attribution + advisory + alert results back to Neon.

**Important caveat on Feature 2 (attribution):** the RandomForest classifier needs *labeled* training data (a `source_label` per hotspot) to learn from. Your `hotspots` table doesn't have that until your team manually labels some historical hotspots or an inspector confirms a few. Until then, `main.py` keeps training on mock labeled data even in real-DB mode — inference still happens on your real hotspot features, only the training set is synthetic. Swap `_training_df` in `main.py` to a real labeled query once you have ~50+ labeled examples.

**Same caveat applies to Feature 1 (prediction):** it needs enough real historical days (ideally 60+) with weather/traffic features attached before switching `_prediction_training_df` from `generate_prediction_training_data()` to a real query — a LightGBM model trained on a handful of real days will overfit badly.

**Feature 8 (chat) real-DB note:** the knowledge corpus (`data/knowledge_corpus.py`) is static reference text, not a DB table — nothing to swap there. What *does* still route to real data in DB mode is the live-context grounding (current AQI + attributed source for the `ward` passed in `/api/chat`), which reuses the same forecast/attribution pipeline as Features 1 & 2.

## Swapping mock data for real feeds

`data/mock_data.py` generates synthetic hotspot features, citizen profiles, weather/traffic conditions, emission sources, sub-hourly readings, alert dispatch history, enforcement queue snapshots, intervention ROI series, and 400 days of historical AQI so all twelve agents can be built/demoed before the ingestion pipeline (CAAQMS, Overpass land-use, NASA FIRMS, weather APIs) is live. Each generator's output schema matches what the real PostGIS tables will produce — swap the call sites in `main.py` for real DB queries without touching agent logic.

## What to plug in next
- Replace `generate_hotspot_features()` with a real query joining `readings` + `emission_sources` + Overpass land-use.
- Replace `generate_citizen_profile()` / hardcoded profiles with the `citizens` table (added by migration 002).
- Replace `generate_historical_aqi()` with a `SELECT ward, date, avg(aqi) FROM readings GROUP BY ...` query against PostGIS.
- Replace `generate_current_conditions()` and `generate_prediction_training_data()` with real weather (Open-Meteo) + traffic feeds once ingestion is live.
- Replace `generate_emission_sources()` with a real query against the `emission_sources` table.
- Replace `generate_realtime_readings()` with a live sub-hourly `readings` query (last N minutes) for the Emergency Detection Agent.
- Replace `generate_alert_feed()` with `db.repository.fetch_recent_alerts()` (already wired automatically once `DATABASE_URL` is set).
- Replace `generate_enforcement_queue_snapshot()` / `generate_intervention_roi_series()` with `db.repository.fetch_enforcement_status_counts()` / `fetch_intervention_roi_timeseries()` (already wired automatically once `DATABASE_URL` is set).
- Swap `agents/chat_agent.py`'s TF-IDF retrieval for a Sentence-Transformers encoder, and its templated `_synthesize_answer()` for a real LLM call, once an embedding model / LLM API key is available -- the retrieval/answer-assembly plumbing around it doesn't need to change.
- Swap `agents/alert_agent.py`'s `_send()` mock gateway for a real Twilio (SMS/IVR) or FCM/APNs (push) call once credentials are available.
- Add more languages to `TEMPLATES` / `VULNERABILITY_ADDENDA` in `advisory_agent.py` (Kannada, Tamil) — it's a pure data addition, no code change needed.

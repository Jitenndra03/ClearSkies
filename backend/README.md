# AirPulse — Features 2, 5, 10

Working implementations of three system features from the AirPulse plan:

- **Feature 2 — Pollution Source Attribution** (`agents/attribution_agent.py`): RandomForest classifier that attributes a hotspot to traffic/construction/industrial/dust/stubble-burning with a confidence score and human-readable evidence.
- **Feature 5 — Citizen Health Advisory** (`agents/advisory_agent.py`): Personalized, multilingual (English + Hindi, easily extendable) health advisories based on forecast AQI + vulnerability profile (asthma, elderly, outdoor worker).
- **Feature 10 — Trend Analysis** (`agents/trend_agent.py`): Mines historical AQI for weekday/weekend deltas, monthly seasonality, festival-linked spikes (Diwali, Holi, stubble season), and statistical anomaly days.

All three are wired into a FastAPI app (`api/main.py`) so the frontend team can integrate immediately.

## Setup

```bash
pip install -r requirements.txt
```

## Run each agent standalone (prints a demo result)

```bash
python3 agents/attribution_agent.py
python3 agents/advisory_agent.py
python3 agents/trend_agent.py
```

## Run the API

```bash
uvicorn api.main:app --reload --port 8000
```

Then open `http://localhost:8000/docs` for interactive Swagger docs, or:

```bash
# Attribution
curl -X POST http://localhost:8000/api/attribution \
  -H "Content-Type: application/json" \
  -d '{"ward":"Ward-3","traffic_density_idx":0.2,"construction_permit_density":0.05,"industrial_stack_count":5,"thermal_anomaly_count":0,"dust_landuse_pct":0.05,"pm25":95}'

# Advisory
curl -X POST http://localhost:8000/api/advisory \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u9","ward":"Ward-2","language":"hi","conditions":["asthma"],"forecast_aqi":320}'

# Trends
curl http://localhost:8000/api/trends/Ward-4
curl http://localhost:8000/api/trends
```

## Connecting to Neon (real database)

Your live Neon schema already exists (`db/migrations/001_init_schema.sql` mirrors it — **don't re-run 001, it's reference only**). It's missing two things the agents need: a `citizens` table (for personalized advisories) and raw feature columns on `hotspots` (for attribution training/audit). Run the additive migration to add those without touching existing data:

1. Copy `.env.example` to `.env` and paste your Neon **pooled** connection string (Neon Console → your project → Connection Details). Keep `sslmode=require`.
2. Load it:
   ```bash
   export $(cat .env | xargs)
   ```
3. Run the additive migration:
   ```bash
   psql "$DATABASE_URL" -f db/migrations/002_add_attribution_and_citizens.sql
   ```
4. Seed at least one row in `citizens` so `/api/advisory` has someone real to look up (or keep passing profile fields directly in the request, which works without the table too).
5. Start the API — it auto-detects `DATABASE_URL` and switches from mock to real data for trends/advisories, and writes attribution + advisory results back to Neon:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```

**Important caveat on Feature 2 (attribution):** the RandomForest classifier needs *labeled* training data (a `source_label` per hotspot) to learn from. Your `hotspots` table doesn't have that until your team manually labels some historical hotspots or an inspector confirms a few. Until then, `api/main.py` keeps training on mock labeled data even in real-DB mode — inference still happens on your real hotspot features, only the training set is synthetic. Swap `_training_df` in `api/main.py` to a real labeled query once you have ~50+ labeled examples.

## Swapping mock data for real feeds

`data/mock_data.py` generates synthetic hotspot features, citizen profiles, and 400 days of historical AQI so all three agents can be built/demoed before the ingestion pipeline (CAAQMS, Overpass land-use, NASA FIRMS) is live. Each generator's output schema matches what the real PostGIS tables will produce — swap the call sites in `api/main.py` for real DB queries without touching agent logic.

## What to plug in next
- Replace `generate_hotspot_features()` with a real query joining `readings` + `emission_sources` + Overpass land-use.
- Replace `generate_citizen_profile()` / hardcoded profiles with the `citizen_advisories` subscriber table.
- Replace `generate_historical_aqi()` with a `SELECT ward, date, avg(aqi) FROM readings GROUP BY ...` query against PostGIS.
- Add more languages to `TEMPLATES` / `VULNERABILITY_ADDENDA` in `advisory_agent.py` (Kannada, Tamil) — it's a pure data addition, no code change needed.

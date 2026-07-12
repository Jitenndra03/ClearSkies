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

## Swapping mock data for real feeds

`data/mock_data.py` generates synthetic hotspot features, citizen profiles, and 400 days of historical AQI so all three agents can be built/demoed before the ingestion pipeline (CAAQMS, Overpass land-use, NASA FIRMS) is live. Each generator's output schema matches what the real PostGIS tables will produce — swap the call sites in `api/main.py` for real DB queries without touching agent logic.

## What to plug in next
- Replace `generate_hotspot_features()` with a real query joining `readings` + `emission_sources` + Overpass land-use.
- Replace `generate_citizen_profile()` / hardcoded profiles with the `citizen_advisories` subscriber table.
- Replace `generate_historical_aqi()` with a `SELECT ward, date, avg(aqi) FROM readings GROUP BY ...` query against PostGIS.
- Add more languages to `TEMPLATES` / `VULNERABILITY_ADDENDA` in `advisory_agent.py` (Kannada, Tamil) — it's a pure data addition, no code change needed.

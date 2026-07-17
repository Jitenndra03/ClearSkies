"""
main.py
-------
FastAPI wiring for System Features 1, 2, 3, 4, 5, 7, and 11 so the frontend
team can hit real endpoints immediately, using mock data until the
ingestion pipeline is connected.

(Note: Trend Analysis is Feature 7 in the plan's Section 2 list, not
Feature 10 as an earlier version of this file said -- fixed here.)

Run: uvicorn api.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from agents.attribution_agent import PollutionAttributionAgent
from agents.advisory_agent import CitizenAdvisoryAgent, CitizenProfile
from agents.trend_agent import TrendAnalysisAgent
<<<<<<< HEAD
from agents.prediction_agent import AQIPredictionAgent
from agents.recommendation_agent import RecommendationAgent
from agents.enforcement_agent import EnforcementPrioritizationAgent
from agents.emergency_agent import EmergencyDetectionAgent
from data.mock_data import (
    generate_hotspot_features,
    generate_historical_aqi,
    generate_prediction_training_data,
    generate_current_conditions,
    generate_emission_sources,
    generate_realtime_readings,
    FESTIVALS_2025_26,
)
from db.database import is_db_configured

app = FastAPI(title="AirPulse ")
=======
from agents.heatmap_agent import HeatmapAgent
from agents.comparison_agent import MultiCityComparisonAgent
from agents.emergency_agent import EmergencyDetectionAgent
from data.mock_data import (
    generate_hotspot_features, generate_historical_aqi, FESTIVALS_2025_26,
    generate_station_snapshot, generate_multi_city_history,
    generate_source_breakdown_by_city, generate_station_reading_series,
    CITIES,
)
from db.database import is_db_configured

app = FastAPI(title="AirPulse — Features 2, 5, 6, 10, 11")
>>>>>>> c72ba7a (Implemented the rest of the features)

USING_REAL_DB = is_db_configured()

if USING_REAL_DB:
    # Real Neon data. Note: attribution training still needs labeled data --
    # if your hotspots table doesn't have source_label populated yet, keep
    # training on mock data (which has labels) and only swap inference/trend
    # data sources to real DB. Adjust the two lines below once you have
    # labeled hotspot data to train on.
    from db.repository import fetch_hotspot_features, fetch_historical_aqi
    _training_df = generate_hotspot_features()  # swap to a labeled real query once available
    _historical_df = fetch_historical_aqi()
else:
    _training_df = generate_hotspot_features()
    _historical_df = generate_historical_aqi()

# --- Startup: train models once ---
attribution_agent = PollutionAttributionAgent()
_training_report = attribution_agent.train(_training_df)

prediction_agent = AQIPredictionAgent()
_prediction_training_df = generate_prediction_training_data()  # swap to real historical query once you have enough real days
_prediction_metrics = prediction_agent.train(_prediction_training_df)

advisory_agent = CitizenAdvisoryAgent()
trend_agent = TrendAnalysisAgent()
<<<<<<< HEAD
recommendation_agent = RecommendationAgent()
enforcement_agent = EnforcementPrioritizationAgent()
emergency_agent = EmergencyDetectionAgent()

_emission_sources_df = generate_emission_sources()  # swap to a real `emission_sources` table query
=======
heatmap_agent = HeatmapAgent()
comparison_agent = MultiCityComparisonAgent()
emergency_agent = EmergencyDetectionAgent()
>>>>>>> c72ba7a (Implemented the rest of the features)


# ---------- Feature 2: Source Attribution ----------

class HotspotInput(BaseModel):
    ward: str
    traffic_density_idx: float
    construction_permit_density: float
    industrial_stack_count: int
    thermal_anomaly_count: int
    dust_landuse_pct: float
    pm25: float


class HotspotInputWithId(HotspotInput):
    hotspot_id: Optional[int] = None  # pass this to persist the result back to Neon


@app.post("/api/attribution")
def attribute_hotspot(hotspot: HotspotInputWithId):
    import pandas as pd
    row = pd.Series(hotspot.dict(exclude={"hotspot_id"}))
    result = attribution_agent.attribute(row)

    if USING_REAL_DB and hotspot.hotspot_id is not None:
        from db.repository import insert_hotspot_attribution
        insert_hotspot_attribution(hotspot.hotspot_id, result.predicted_source, result.confidence)

    return {
        "ward": result.ward,
        "predicted_source": result.predicted_source,
        "confidence": result.confidence,
        "all_probabilities": result.all_probabilities,
        "evidence": result.evidence,
    }


@app.get("/api/attribution/model-report")
def get_model_report():
    return {"classification_report": _training_report}


# ---------- Feature 5: Citizen Health Advisory ----------

class AdvisoryRequest(BaseModel):
    user_id: str
    ward: str
    language: str = "en"
    conditions: Optional[List[str]] = None
    elderly: bool = False
    outdoor_worker: bool = False
    forecast_aqi: float


@app.post("/api/advisory")
def get_advisory(req: AdvisoryRequest):
    profile = CitizenProfile(
        user_id=req.user_id,
        ward=req.ward,
        language=req.language,
        conditions=req.conditions or [],
        elderly=req.elderly,
        outdoor_worker=req.outdoor_worker,
    )
    advisory = advisory_agent.generate(profile, req.forecast_aqi)

    if USING_REAL_DB:
        from db.repository import insert_advisory
        insert_advisory(advisory.ward, advisory.language, advisory.message, advisory.risk_level)

    return {
        "user_id": advisory.user_id,
        "ward": advisory.ward,
        "language": advisory.language,
        "risk_level": advisory.risk_level,
        "forecast_aqi": advisory.forecast_aqi,
        "message": advisory.message,
    }


# ---------- Feature 7: Trend Analysis ----------

@app.get("/api/trends/{ward}")
def get_ward_trends(ward: str):
    if ward not in _historical_df["ward"].unique():
        raise HTTPException(status_code=404, detail=f"No data for ward '{ward}'")
    report = trend_agent.analyze_ward(_historical_df, ward, FESTIVALS_2025_26)
    return {
        "ward": report.ward,
        "avg_aqi": report.avg_aqi,
        "weekday_avg": report.weekday_avg,
        "weekend_avg": report.weekend_avg,
        "weekday_vs_weekend_delta": report.weekday_vs_weekend_delta,
        "monthly_avg": report.monthly_avg,
        "peak_month": report.peak_month,
        "festival_spikes": report.festival_spikes,
        "anomaly_days": report.anomaly_days,
    }


@app.get("/api/trends")
def get_all_trends():
    reports = trend_agent.analyze_all_wards(_historical_df, FESTIVALS_2025_26)
    return {
        ward: {
            "avg_aqi": r.avg_aqi,
            "peak_month": r.peak_month,
            "festival_spikes": r.festival_spikes,
            "anomaly_count": len(r.anomaly_days),
        }
        for ward, r in reports.items()
    }


# ---------- Feature 6: Geospatial Heatmaps ----------

@app.get("/api/heatmap/{city}")
def get_heatmap(city: str, pollutant: str = "aqi", resolution: int = 40):
    if USING_REAL_DB:
        from db.repository import fetch_latest_station_readings
        station_df = fetch_latest_station_readings(city)
    else:
        station_df = generate_station_snapshot()

    if station_df.empty:
        raise HTTPException(status_code=404, detail=f"No station data found for {city}")

    heatmap_agent.grid_resolution = resolution
    result = heatmap_agent.interpolate(station_df, city=city, pollutant=pollutant)
    return {
        "city": result.city,
        "pollutant": result.pollutant,
        "grid": result.grid,
        "stations": result.stations,
    }


# ---------- Feature 10: Multi-city Comparison ----------
# (Not to be confused with the "Feature 10" label on TrendAnalysisAgent
# above -- per the original plan's numbering that one is Feature 7. This
# is the actual Feature 10: cross-city benchmarking.)

@app.get("/api/compare")
def compare_cities(cities: Optional[str] = None, days: int = 30):
    city_list = [c.strip() for c in cities.split(",")] if cities else CITIES

    if USING_REAL_DB:
        from db.repository import (
            fetch_multi_city_summary, fetch_intervention_summary, fetch_source_breakdown_by_city,
        )
        history_df = fetch_multi_city_summary(city_list, days)
        intervention_df = fetch_intervention_summary(city_list, days)
        source_df = fetch_source_breakdown_by_city(city_list, days)
        # merge intervention counts/drops into the history frame's per-city rows
        history_df = history_df.merge(
            intervention_df.rename(columns={"intervention_count": "_ic", "avg_aqi_drop": "_drop"}),
            on="city", how="left",
        )
        history_df["intervention_logged"] = history_df["_ic"].fillna(0) > 0
        history_df["aqi_drop"] = history_df["_drop"].fillna(0)
    else:
        history_df = generate_multi_city_history(days=days)
        source_df = generate_source_breakdown_by_city()

    entries = comparison_agent.compare(history_df, source_df)
    return {
        "period_days": days,
        "cities": [
            {
                "city": e.city,
                "avg_aqi": e.avg_aqi,
                "intervention_count": e.intervention_count,
                "avg_aqi_drop_per_intervention": e.avg_aqi_drop_per_intervention,
                "source_breakdown": e.source_breakdown,
            }
            for e in entries
        ],
    }


# ---------- Feature 11: Emergency Pollution Detection ----------

class StationCheckRequest(BaseModel):
    station_id: int
    hours: int = 48


@app.post("/api/emergency/check")
def check_station_for_spike(req: StationCheckRequest):
    """
    Checks a single station's recent readings for a statistically abnormal
    spike. Intended to be called inline by the ingestion scheduler on every
    cycle (15-60 min) for every active station -- exposed here as an
    endpoint too so the frontend/demo can trigger it on demand.
    """
    if USING_REAL_DB:
        from db.repository import fetch_recent_readings
        series = fetch_recent_readings(req.station_id, hours=req.hours)
    else:
        series = generate_station_reading_series(station_id=req.station_id, hours=req.hours)

    alert = emergency_agent.check_station(series)
    if alert is None:
        return {"station_id": req.station_id, "spike_detected": False}

    return {
        "station_id": alert.station_id,
        "spike_detected": True,
        "timestamp": alert.timestamp,
        "pm25": alert.pm25,
        "zscore": alert.zscore,
        "priority": alert.priority,
        "message": alert.message,
    }


@app.get("/api/emergency/scan/{city}")
def scan_city_for_spikes(city: str):
    """Checks every active station in a city in one call -- what the
    Admin Panel's 'run emergency scan' button would hit."""
    if USING_REAL_DB:
        from db.repository import fetch_all_active_station_ids, fetch_recent_readings
        station_ids = fetch_all_active_station_ids(city)
        readings_by_station = {sid: fetch_recent_readings(sid) for sid in station_ids}
    else:
        # mock mode: pretend there are 3 stations, one of which is spiking
        readings_by_station = {
            sid: generate_station_reading_series(station_id=sid) for sid in [1, 2, 3]
        }

    alerts = emergency_agent.check_all_stations(readings_by_station)
    return {
        "city": city,
        "stations_checked": len(readings_by_station),
        "alerts": [
            {
                "station_id": a.station_id, "timestamp": a.timestamp, "pm25": a.pm25,
                "zscore": a.zscore, "priority": a.priority, "message": a.message,
            }
            for a in alerts
        ],
    }


@app.get("/")
def root():
<<<<<<< HEAD
    return {"status": "AirPulse features 1 (prediction), 2 (attribution), 3 (recommendation), 4 (enforcement), 5 (advisory), 7 (trends), 11 (emergency) are live"}


# ---------- Feature 1: Hyperlocal AQI Prediction ----------

@app.get("/api/forecast/{ward}")
def get_forecast(ward: str, horizon_hr: int = 24):
    conditions = generate_current_conditions(ward)  # swap to a real current-conditions query once weather/traffic ingestion is live
    forecast = prediction_agent.predict(conditions, horizon_hr)
    return {
        "ward": forecast.ward,
        "horizon_hr": forecast.horizon_hr,
        "predicted_aqi": forecast.predicted_aqi,
        "lower_bound": forecast.lower_bound,
        "upper_bound": forecast.upper_bound,
        "confidence": forecast.confidence,
    }


@app.get("/api/forecast/{ward}/multi-horizon")
def get_multi_horizon_forecast(ward: str):
    conditions = generate_current_conditions(ward)
    forecasts = prediction_agent.predict_multi_horizon(conditions)
    return [
        {
            "horizon_hr": f.horizon_hr,
            "predicted_aqi": f.predicted_aqi,
            "lower_bound": f.lower_bound,
            "upper_bound": f.upper_bound,
            "confidence": f.confidence,
        }
        for f in forecasts
    ]


@app.get("/api/forecast/model-report")
def get_forecast_model_report():
    return _prediction_metrics


# ---------- Feature 3: AI Intervention Recommendation Engine ----------

class RecommendationRequest(BaseModel):
    ward: str
    source: str  # traffic / construction / industrial / dust / stubble_burning
    forecast_aqi: float
    festival_context: Optional[str] = None


@app.post("/api/recommendations")
def get_recommendations(req: RecommendationRequest):
    bundle = recommendation_agent.recommend(
        ward=req.ward, source=req.source, forecast_aqi=req.forecast_aqi, festival_context=req.festival_context
    )
    return {
        "ward": bundle.ward,
        "source": bundle.source,
        "severity": bundle.severity,
        "forecast_aqi": bundle.forecast_aqi,
        "festival_context": bundle.festival_context,
        "actions": [
            {"action": a.action, "responsible_role": a.responsible_role, "urgency_hours": a.urgency_hours}
            for a in bundle.actions
        ],
    }


@app.get("/api/recommendations/{ward}")
def get_recommendations_from_pipeline(ward: str):
    """
    Convenience endpoint: chains attribution + forecast automatically to
    produce recommendations without the caller needing to run each agent
    manually first. Uses each ward's synthetic hotspot row for attribution.
    """
    import pandas as pd
    ward_hotspots = _training_df[_training_df["ward"] == ward]
    if ward_hotspots.empty:
        raise HTTPException(status_code=404, detail=f"No hotspot data for ward '{ward}'")
    attribution = attribution_agent.attribute(ward_hotspots.iloc[0])

    conditions = generate_current_conditions(ward)
    forecast = prediction_agent.predict(conditions, horizon_hr=24)

    bundle = recommendation_agent.recommend_from_attribution_and_forecast(attribution, forecast)
    return {
        "ward": bundle.ward,
        "attributed_source": attribution.predicted_source,
        "attribution_confidence": attribution.confidence,
        "forecast_aqi": forecast.predicted_aqi,
        "severity": bundle.severity,
        "actions": [
            {"action": a.action, "responsible_role": a.responsible_role, "urgency_hours": a.urgency_hours}
            for a in bundle.actions
        ],
    }


# ---------- Feature 4: Smart Enforcement Prioritization ----------

@app.get("/api/enforcement/queue")
def get_enforcement_queue(top_n: int = 10):
    # Ward severity comes from the Prediction Agent's forecast for each ward.
    severity_map = {}
    for ward in _emission_sources_df["ward"].unique():
        conditions = generate_current_conditions(ward)
        forecast = prediction_agent.predict(conditions, horizon_hr=24)
        severity_map[ward] = recommendation_agent.severity_band(forecast.predicted_aqi)

    ranked = enforcement_agent.prioritize(_emission_sources_df, severity_map)
    return [
        {
            "source_id": r.source_id,
            "name": r.name,
            "ward": r.ward,
            "type": r.type,
            "priority_score": r.priority_score,
            "reasons": r.reasons,
        }
        for r in ranked[:top_n]
    ]


# ---------- Feature 11: Emergency Pollution Detection ----------

@app.get("/api/emergency/check/{ward}")
def check_emergency(ward: str, simulate_spike: bool = False):
    readings = generate_realtime_readings(ward, spike=simulate_spike)  # swap to a real live readings query
    alert = emergency_agent.check(readings)
    if alert is None:
        return {"ward": ward, "emergency": False}
    return {
        "ward": alert.ward,
        "emergency": True,
        "triggered_at": alert.triggered_at,
        "trigger_type": alert.trigger_type,
        "current_aqi": alert.current_aqi,
        "aqi_delta": alert.aqi_delta,
        "window_minutes": alert.window_minutes,
        "message": alert.message,
    }


@app.get("/api/emergency/check-all")
def check_all_emergencies():
    from data.mock_data import WARDS
    readings_by_ward = {w: generate_realtime_readings(w, spike=(w == "Ward-5")) for w in WARDS}
    alerts = emergency_agent.check_all_wards(readings_by_ward)
    return [
        {
            "ward": a.ward,
            "trigger_type": a.trigger_type,
            "current_aqi": a.current_aqi,
            "message": a.message,
        }
        for a in alerts
    ]
=======
    return {
        "status": (
            "AirPulse features 2 (attribution), 5 (advisory), 7/'10' (trends), "
            "6 (heatmap), 10 (multi-city comparison), 11 (emergency detection) are live"
        )
    }
>>>>>>> c72ba7a (Implemented the rest of the features)

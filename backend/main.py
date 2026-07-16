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
recommendation_agent = RecommendationAgent()
enforcement_agent = EnforcementPrioritizationAgent()
emergency_agent = EmergencyDetectionAgent()

_emission_sources_df = generate_emission_sources()  # swap to a real `emission_sources` table query


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


@app.get("/")
def root():
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

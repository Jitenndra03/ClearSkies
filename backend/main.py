"""
main.py
-------
FastAPI wiring for System Features 2, 5, and 10 so the frontend team can
hit real endpoints immediately, using mock data until the ingestion
pipeline is connected.

Run: uvicorn api.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from agents.attribution_agent import PollutionAttributionAgent
from agents.advisory_agent import CitizenAdvisoryAgent
from agents.trend_agent import TrendAnalysisAgent
from apscheduler.schedulers.background import BackgroundScheduler
from pipeline.ingestion import run_ingestion
from agents.recommendation_agent import RecommendationAgent
from agents.explanation_agent import ExplanationAgent
from data.mock_data import generate_hotspot_features, generate_historical_aqi, FESTIVALS_2025_26
from db.database import is_db_configured

app = FastAPI(title="AirPulse — Features 2, 5, 10")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# --- Startup: train the attribution model once ---
attribution_agent = PollutionAttributionAgent()
_training_report = attribution_agent.train(_training_df)

advisory_agent = CitizenAdvisoryAgent()
trend_agent = TrendAnalysisAgent()


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
    from agents.advisory_agent import CitizenProfile
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


# ---------- Feature 10: Trend Analysis ----------

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


# ---------- Feature: Admin Enforcement Queue ----------

from db.repository import fetch_active_hotspots

@app.get("/api/enforcement-queue")
def get_enforcement_queue():
    agent = RecommendationAgent()
    
    if USING_REAL_DB:
        hotspots = fetch_active_hotspots(limit=10)
    else:
        hotspots = []
        
    if not hotspots:
        hotspots = [
            {"id": "enf-001", "ward": "Shahdara", "source": "industrial", "confidence": 0.88, "aqi": 420},
            {"id": "enf-002", "ward": "Anand Vihar", "source": "vehicular", "confidence": 0.92, "aqi": 390},
            {"id": "enf-003", "ward": "Nehru Nagar", "source": "construction", "confidence": 0.85, "aqi": 350},
        ]
        
    queue = agent.generate(hotspots)
    return {"queue": queue, "generated_at": datetime.utcnow().isoformat()}

# ---------- Feature: Outcome Tracking ----------

class OutcomePayload(BaseModel):
    queue_id: str
    before_aqi: int
    after_aqi: int

outcomes_store: dict = {}

@app.post("/api/enforcement-outcome")
def post_enforcement_outcome(payload: OutcomePayload):
    outcomes_store[payload.queue_id] = {
        "queue_id": payload.queue_id,
        "before_aqi": payload.before_aqi,
        "after_aqi": payload.after_aqi,
        "delta": payload.before_aqi - payload.after_aqi,
        "logged_at": datetime.utcnow().isoformat()
    }
    return {"success": True, "delta": payload.before_aqi - payload.after_aqi}


class ChatPayload(BaseModel):
    query: str
    ward: str
    language: str = "en"
    aqi: int
    source: str = "Unknown"
    confidence: float = 0.0
    risk_level: str = "Unknown"
    peak_month: str = "Unknown"
    weekday_delta: float = 0.0

@app.post("/api/chat")
def post_chat(payload: ChatPayload):
    try:
        agent = ExplanationAgent()
        context = {
            "ward": payload.ward,
            "aqi": payload.aqi,
            "source": payload.source,
            "confidence": round(payload.confidence * 100, 1),
            "risk_level": payload.risk_level,
            "peak_month": payload.peak_month,
            "weekday_delta": payload.weekday_delta
        }
        result = agent.answer(payload.query, context, payload.language)
        return result
    except Exception as e:
        return {"answer": "I'm having trouble connecting right now. Please check the AQI display for current conditions.", "citation": "", "language": payload.language}


@app.get("/")
def root():
    return {"status": "AirPulse features 2 (attribution), 5 (advisory), 10 (trends) are live"}

scheduler = BackgroundScheduler()
scheduler.add_job(run_ingestion, 'interval', minutes=30, id='ingestion_job')

@app.on_event("startup")
async def startup_event():
    scheduler.start()
    import logging
    logging.info("Ingestion scheduler started — running every 30 minutes")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    import logging
    logging.info("Ingestion scheduler stopped")

@app.post("/api/ingest/trigger")
def trigger_ingestion_manual():
    try:
        run_ingestion()
        return {"success": True, "message": "Ingestion completed successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

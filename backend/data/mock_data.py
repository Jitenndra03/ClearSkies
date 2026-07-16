"""
mock_data.py
------------
Synthetic data generators that stand in for the real free-API feeds
(CPCB CAAQMS, Overpass land-use, OSRM traffic, NASA FIRMS thermal anomalies)
so the three agents below can be built, tested, and demoed before the
data-pipeline team wires up live ingestion.

Swap these out for real DB queries / API calls without touching agent logic —
each generator's output schema matches what the real pipeline will produce.
"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

WARDS = [f"Ward-{i}" for i in range(1, 9)]

SOURCE_PROFILES = {
    # ward -> dominant ground-truth source (used only to generate realistic mock data)
    "Ward-1": "traffic",
    "Ward-2": "construction",
    "Ward-3": "industrial",
    "Ward-4": "traffic",
    "Ward-5": "dust",
    "Ward-6": "industrial",
    "Ward-7": "construction",
    "Ward-8": "stubble_burning",
}

FESTIVALS_2025_26 = {
    "Diwali": datetime(2025, 10, 21),
    "Holi": datetime(2026, 3, 4),
    "Harvest/Stubble Season Start": datetime(2025, 10, 1),
}


def generate_hotspot_features(n_per_ward: int = 30) -> pd.DataFrame:
    """
    Generates hotspot-level feature rows: land-use %, traffic density index,
    satellite thermal anomaly count, construction permit density, industrial
    stack count -- the inputs the Attribution Agent consumes.
    """
    rows = []
    for ward in WARDS:
        dominant = SOURCE_PROFILES[ward]
        for _ in range(n_per_ward):
            base = {
                "ward": ward,
                "traffic_density_idx": np.random.uniform(0.1, 0.4),
                "construction_permit_density": np.random.uniform(0.0, 0.2),
                "industrial_stack_count": np.random.poisson(0.5),
                "thermal_anomaly_count": np.random.poisson(0.2),
                "dust_landuse_pct": np.random.uniform(0.0, 0.15),
                "pm25": np.random.uniform(40, 90),
            }
            # bias features toward the ward's dominant source so the
            # classifier has a real signal to learn during the demo
            if dominant == "traffic":
                base["traffic_density_idx"] += np.random.uniform(0.3, 0.5)
                base["pm25"] += 30
            elif dominant == "construction":
                base["construction_permit_density"] += np.random.uniform(0.3, 0.5)
                base["pm25"] += 25
            elif dominant == "industrial":
                base["industrial_stack_count"] += np.random.poisson(3)
                base["pm25"] += 40
            elif dominant == "dust":
                base["dust_landuse_pct"] += np.random.uniform(0.3, 0.5)
                base["pm25"] += 20
            elif dominant == "stubble_burning":
                base["thermal_anomaly_count"] += np.random.poisson(4)
                base["pm25"] += 50

            base["source_label"] = dominant  # ground truth, used for training only
            rows.append(base)
    return pd.DataFrame(rows)


def generate_citizen_profile(user_id: str) -> dict:
    profiles = [
        {"user_id": user_id, "ward": "Ward-1", "language": "en", "conditions": ["asthma"], "outdoor_worker": False, "elderly": False},
        {"user_id": user_id, "ward": "Ward-3", "language": "hi", "conditions": [], "outdoor_worker": True, "elderly": False},
        {"user_id": user_id, "ward": "Ward-6", "language": "hi", "conditions": [], "outdoor_worker": False, "elderly": True},
    ]
    return random.choice(profiles)


def generate_prediction_training_data(days: int = 400) -> pd.DataFrame:
    """
    Historical rows with weather + traffic + lag features + target AQI,
    for training the LightGBM forecasting model (Feature 1).
    """
    hist = generate_historical_aqi(days=days)
    hist["date"] = pd.to_datetime(hist["date"])
    hist = hist.sort_values(["ward", "date"])

    rows = []
    for ward, group in hist.groupby("ward"):
        group = group.reset_index(drop=True)
        for i in range(7, len(group)):  # need 7 days of lag history
            row = group.iloc[i]
            date = row["date"]
            rows.append({
                "ward": ward,
                "date": date,
                "day_of_week": date.weekday(),
                "month": date.month,
                "temp_c": np.random.uniform(10, 35) - (5 if date.month in (12, 1, 2) else 0),
                "humidity_pct": np.random.uniform(30, 85),
                "wind_speed_kmh": np.random.uniform(2, 25),
                "wind_direction_deg": np.random.uniform(0, 360),
                "traffic_density_idx": np.random.uniform(0.2, 0.9),
                "aqi_lag_1": group.iloc[i - 1]["aqi"],
                "aqi_lag_7": group.iloc[i - 7]["aqi"],
                "aqi": row["aqi"],  # target
            })
    return pd.DataFrame(rows)


def generate_current_conditions(ward: str) -> dict:
    """Current weather/traffic snapshot + recent AQI lags, used as inference input for the Prediction Agent."""
    return {
        "ward": ward,
        "day_of_week": datetime.now().weekday(),
        "month": datetime.now().month,
        "temp_c": np.random.uniform(15, 30),
        "humidity_pct": np.random.uniform(35, 80),
        "wind_speed_kmh": np.random.uniform(3, 20),
        "wind_direction_deg": np.random.uniform(0, 360),
        "traffic_density_idx": np.random.uniform(0.3, 0.8),
        "aqi_lag_1": np.random.uniform(80, 220),
        "aqi_lag_7": np.random.uniform(80, 220),
    }


def generate_emission_sources(n: int = 20) -> pd.DataFrame:
    """
    Registered emission sources with permit + inspection history, used by
    the Enforcement Prioritization Agent (Feature 4).
    """
    types = ["industry", "construction", "waste_burning_site", "diesel_depot"]
    rows = []
    for i in range(n):
        rows.append({
            "id": i + 1,
            "ward": random.choice(WARDS),
            "type": random.choice(types),
            "name": f"Site-{i+1}",
            "permit_status": random.choice(["valid", "expired", "unregistered"]),
            "days_since_last_inspection": random.choice([5, 15, 45, 90, 200, 400]),
            "distance_to_nearest_hotspot_km": round(np.random.uniform(0.1, 3.0), 2),
        })
    return pd.DataFrame(rows)


def generate_realtime_readings(ward: str, spike: bool = True) -> pd.DataFrame:
    """
    Sub-hourly AQI readings over the last few hours for a single ward, used
    by the Emergency Pollution Detection Agent (Feature 11). If spike=True,
    injects a sudden jump in the most recent readings to simulate a real
    emergency (e.g. stubble burning plume, industrial upset) for demo/testing.
    """
    now = datetime.now()
    timestamps = [now - timedelta(minutes=15 * i) for i in range(12)][::-1]  # last 3 hours, 15-min steps
    base = np.random.uniform(90, 130)
    readings = [base + np.random.normal(0, 5) for _ in timestamps]

    if spike:
        # last 3 readings ramp up sharply -- simulates a fast-onset emergency
        readings[-3] += 60
        readings[-2] += 130
        readings[-1] += 220

    return pd.DataFrame({"ward": ward, "timestamp": timestamps, "aqi": [round(r, 1) for r in readings]})


def generate_historical_aqi(days: int = 400) -> pd.DataFrame:
    """
    Generates a daily AQI time series per ward with:
      - a mild upward winter seasonal bump
      - weekday/weekend traffic effect
      - festival spikes (Diwali, harvest/stubble season)
    so the Trend Analysis agent has real patterns to detect.
    """
    start = datetime.now() - timedelta(days=days)
    rows = []
    for ward in WARDS:
        base_level = np.random.uniform(90, 140)
        for d in range(days):
            date = start + timedelta(days=d)
            seasonal = 30 * np.sin((date.timetuple().tm_yday / 365) * 2 * np.pi + np.pi)  # peaks in winter
            weekday_effect = -10 if date.weekday() >= 5 else 5  # weekends slightly cleaner
            noise = np.random.normal(0, 8)

            festival_bump = 0
            for name, fdate in FESTIVALS_2025_26.items():
                if 0 <= (date - fdate).days <= 3:
                    festival_bump += 60 if name == "Diwali" else 35

            aqi = max(20, base_level + seasonal + weekday_effect + noise + festival_bump)
            rows.append({"ward": ward, "date": date.date(), "aqi": round(aqi, 1)})
    return pd.DataFrame(rows)

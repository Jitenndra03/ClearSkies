import os
import sys
import numpy as np
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Setup paths and environment
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from sqlalchemy import create_engine, text

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DELHI_WARDS = [
    {"name": "Shahdara", "lat": 28.6692, "lon": 77.2836},
    {"name": "Anand Vihar", "lat": 28.6469, "lon": 77.3152},
    {"name": "Nehru Nagar", "lat": 28.5672, "lon": 77.2503},
    {"name": "Okhla Phase-II", "lat": 28.5244, "lon": 77.2726},
    {"name": "Rohini", "lat": 28.7041, "lon": 77.1025},
    {"name": "ITO", "lat": 28.6289, "lon": 77.2409},
    {"name": "Dwarka", "lat": 28.5921, "lon": 77.0460},
    {"name": "Vasant Kunj", "lat": 28.5200, "lon": 77.1500},
    {"name": "Paharganj", "lat": 28.6429, "lon": 77.2097},
    {"name": "Karol Bagh", "lat": 28.6520, "lon": 77.1900},
]

BASE_AQI_BY_WARD = {
    "Shahdara": 220, "Anand Vihar": 210, "Nehru Nagar": 195,
    "Okhla Phase-II": 185, "Rohini": 175, "ITO": 165,
    "Dwarka": 150, "Vasant Kunj": 140, "Paharganj": 180, "Karol Bagh": 170
}

CITIZENS = [
    {"user_id": "demo", "ward": "Shahdara", "language": "en", "vulnerability": "outdoor_worker"},
    {"user_id": "demo_hi", "ward": "Anand Vihar", "language": "hi", "vulnerability": "elderly"},
    {"user_id": "u001", "ward": "Rohini", "language": "en", "vulnerability": "child"},
    {"user_id": "u002", "ward": "ITO", "language": "hi", "vulnerability": "respiratory"},
    {"user_id": "u003", "ward": "Dwarka", "language": "en", "vulnerability": "none"},
    {"user_id": "u004", "ward": "Vasant Kunj", "language": "hi", "vulnerability": "elderly"},
]

def generate_aqi(ward_name, date, hour):
    base = BASE_AQI_BY_WARD[ward_name]
    month = date.month
    month_factor = {1:1.4, 2:1.3, 3:1.1, 4:1.0, 5:1.0,
                    6:0.8, 7:0.7, 8:0.75, 9:0.85, 10:1.2, 11:1.5, 12:1.45}
    hour_factor = 1.3 if hour in [7,8,9,18,19,20] else 0.85 if hour in [2,3,4] else 1.0
    weekend_factor = 0.85 if date.weekday() >= 5 else 1.0
    noise = np.random.uniform(0.88, 1.12)
    return int(base * month_factor[month] * hour_factor * weekend_factor * noise)

def run_seed():
    engine = create_engine(os.environ.get("DATABASE_URL"))

    # --- Phase 1: Wards (separate transaction) ---
    logger.info("Seeding wards...")
    with engine.begin() as conn:
        ward_insert_sql = text("""
            INSERT INTO wards (name, city, geometry)
            VALUES (:name, 'Delhi',
                ST_MakeEnvelope(:lon - 0.02, :lat - 0.02, :lon + 0.02, :lat + 0.02, 4326))
            ON CONFLICT (name) DO NOTHING
        """)
        for ward in DELHI_WARDS:
            conn.execute(ward_insert_sql, {"name": ward["name"], "lat": ward["lat"], "lon": ward["lon"]})
    logger.info("Wards done.")

    # --- Phase 2: Stations (separate transaction) ---
    logger.info("Seeding stations...")
    with engine.begin() as conn:
        station_insert_sql = text("""
            INSERT INTO stations (name, lat, lon, ward_id)
            VALUES (:name, :lat, :lon, (SELECT id FROM wards WHERE name = :ward_name LIMIT 1))
            ON CONFLICT (name) DO NOTHING
        """)
        for ward in DELHI_WARDS:
            station_name = f"{ward['name']} CAAQMS"
            conn.execute(station_insert_sql, {"name": station_name, "lat": ward["lat"], "lon": ward["lon"], "ward_name": ward["name"]})
    logger.info("Stations done.")

    # --- Phase 3: Readings (bulk insert, separate transactions per batch) ---
    logger.info("Seeding readings...")
    # Get station ids first
    with engine.connect() as conn:
        stations_res = conn.execute(text("SELECT id, name FROM stations")).mappings().all()
        station_map = {row["name"].replace(" CAAQMS", ""): row["id"] for row in stations_res}

    now = datetime.utcnow()
    hours = [0, 3, 6, 9, 12, 15, 18, 21]
    inserted_readings = 0

    # Build all reading rows in memory first
    all_rows = []
    for i in range(45):
        d = now - timedelta(days=i)
        for ward in DELHI_WARDS:
            ward_name = ward["name"]
            if ward_name not in station_map:
                continue
            station_id = station_map[ward_name]
            for h in hours:
                dt = d.replace(hour=h, minute=0, second=0, microsecond=0)
                aqi = generate_aqi(ward_name, dt, h)
                # Diwali spike
                if dt.month == 10 and dt.day in [20, 21, 22, 23, 24]:
                    aqi = int(aqi * 1.8)
                pm25 = round(aqi * 0.4, 2)
                pm10 = round(aqi * 0.7, 2)
                all_rows.append({
                    "station_id": station_id,
                    "timestamp": dt,
                    "pm25": pm25,
                    "pm10": pm10,
                    "aqi": aqi,
                    "wind_speed": 10.0,
                    "temperature": 25.0,
                    "humidity": 50.0
                })

    # Insert in batches of 500, each batch its own transaction
    readings_sql = text("""
        INSERT INTO readings (station_id, timestamp, pm25, pm10, aqi, wind_speed, temperature, humidity)
        VALUES (:station_id, :timestamp, :pm25, :pm10, :aqi, :wind_speed, :temperature, :humidity)
        ON CONFLICT DO NOTHING
    """)
    BATCH_SIZE = 500
    for start in range(0, len(all_rows), BATCH_SIZE):
        batch = all_rows[start:start + BATCH_SIZE]
        with engine.begin() as conn:
            conn.execute(readings_sql, batch)
        inserted_readings += len(batch)
        logger.info(f"  Readings batch: {inserted_readings}/{len(all_rows)}")

    logger.info(f"Readings done: {inserted_readings} rows.")

    # --- Phase 4: Citizens (separate transaction) ---
    logger.info("Seeding citizens...")
    with engine.begin() as conn:
        citizen_sql = text("""
            INSERT INTO citizens (id, ward_id, language, conditions, outdoor_worker, elderly)
            VALUES (:user_id, (SELECT id FROM wards WHERE name = :ward LIMIT 1), :language, :conditions, :outdoor, :elderly)
            ON CONFLICT (id) DO NOTHING
        """)
        for c in CITIZENS:
            v = c["vulnerability"]
            outdoor = True if v == "outdoor_worker" else False
            elderly = True if v == "elderly" else False
            conditions = f"{{{v}}}" if v in ["respiratory", "asthma"] else "{}"
            conn.execute(citizen_sql, {
                "user_id": c["user_id"],
                "ward": c["ward"],
                "language": c["language"],
                "conditions": conditions,
                "outdoor": outdoor,
                "elderly": elderly
            })
    logger.info("Citizens done.")

    print("[OK] Wards: 10 rows")
    print("[OK] Stations: 10 rows")
    print(f"[OK] Readings: ~{inserted_readings} rows")
    print("[OK] Citizens: 6 rows")
    print("Seed complete.")

if __name__ == "__main__":
    run_seed()

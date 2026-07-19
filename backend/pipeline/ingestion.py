import os
import sys
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

# Setup paths and environment
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

LATEST_WEATHER = {"wind_speed": 0, "temperature": 25, "humidity": 50}

def fetch_cpcb_aqi():
    try:
        endpoint = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
        params = {
            "api-key": os.environ.get("CPCB_API_KEY", ""),
            "format": "json",
            "filters[state]": "Delhi",
            "limit": 100
        }
        res = requests.get(endpoint, params=params, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        if "records" not in data:
            return None
        
        parsed = []
        for record in data["records"]:
            try:
                lat = float(record.get("latitude", 0))
                lon = float(record.get("longitude", 0))
                if lat == 0 or lon == 0:
                    continue
                parsed.append({
                    "station_name": record.get("station"),
                    "lat": lat,
                    "lon": lon,
                    "pm25": float(record.get("pollutant_avg", 0)),
                    "aqi": int(record.get("aqi", 0)),
                    "timestamp": datetime.utcnow()
                })
            except Exception as e:
                logger.warning(f"Failed to parse CPCB record: {e}")
        return parsed
    except Exception as e:
        logger.warning(f"CPCB fetch failed: {e}")
        return None

def fetch_openaq_fallback():
    try:
        endpoint = "https://api.openaq.org/v2/latest"
        params = {"city": "Delhi", "limit": 50, "parameter": "pm25"}
        res = requests.get(endpoint, params=params, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        if "results" not in data:
            return None
        
        parsed = []
        for r in data["results"]:
            try:
                coords = r.get("coordinates", {})
                lat = float(coords.get("latitude", 0))
                lon = float(coords.get("longitude", 0))
                if lat == 0 or lon == 0:
                    continue
                
                pm25 = 0
                for m in r.get("measurements", []):
                    if m.get("parameter") == "pm25":
                        pm25 = float(m.get("value", 0))
                        break
                
                parsed.append({
                    "station_name": r.get("location"),
                    "lat": lat,
                    "lon": lon,
                    "pm25": pm25,
                    "aqi": int(pm25 * 3), # Rough mockup if AQI not present
                    "timestamp": datetime.utcnow()
                })
            except Exception as e:
                logger.warning(f"Failed to parse OpenAQ record: {e}")
        return parsed
    except Exception as e:
        logger.warning(f"OpenAQ fallback failed: {e}")
        return None

def fetch_weather():
    global LATEST_WEATHER
    try:
        endpoint = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 28.6139,
            "longitude": 77.2090,
            "current_weather": True,
            "hourly": "relativehumidity_2m,windspeed_10m,temperature_2m",
            "forecast_days": 1
        }
        res = requests.get(endpoint, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            hourly = data.get("hourly", {})
            LATEST_WEATHER["wind_speed"] = hourly.get("windspeed_10m", [0])[0]
            LATEST_WEATHER["temperature"] = hourly.get("temperature_2m", [25])[0]
            LATEST_WEATHER["humidity"] = hourly.get("relativehumidity_2m", [50])[0]
    except Exception as e:
        logger.warning(f"Weather fetch failed, using defaults. Error: {e}")

import csv
from io import StringIO

def fetch_firms_data():
    try:
        api_key = os.environ.get("NASA_FIRMS_MAP_KEY")
        if not api_key:
            logger.info("NASA_FIRMS_MAP_KEY not set. Skipping FIRMS integration.")
            return []
            
        # NRT VIIRS 375m data for India (IND) for the last 1 day
        endpoint = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{api_key}/VIIRS_SNPP_NRT/IND/1"
        res = requests.get(endpoint, timeout=15)
        if res.status_code != 200:
            logger.warning(f"FIRMS API returned {res.status_code}")
            return []
            
        csv_data = StringIO(res.text)
        reader = csv.DictReader(csv_data)
        
        anomalies = []
        for row in reader:
            try:
                lat = float(row['latitude'])
                lon = float(row['longitude'])
                anomalies.append({"lat": lat, "lon": lon})
            except (KeyError, ValueError):
                continue
                
        return anomalies
    except Exception as e:
        logger.warning(f"Failed to fetch FIRMS data: {e}")
        return []

def run_ingestion():
    logger.info("Ingestion started")
    
    # Step 1 & 2
    records = fetch_cpcb_aqi()
    if records is None or len(records) == 0:
        logger.warning("CPCB data invalid or missing, falling back to OpenAQ")
        records = fetch_openaq_fallback()
        if records is None:
            logger.warning("Both CPCB and OpenAQ failed. Falling back to mock live data.")
            import random
            records = []
            for i in range(1, 11):
                lat = 28.6 + random.uniform(-0.1, 0.1)
                lon = 77.2 + random.uniform(-0.1, 0.1)
                pm25 = random.uniform(50, 300)
                records.append({
                    "station_name": f"Mock Station {i}",
                    "lat": lat,
                    "lon": lon,
                    "pm25": pm25,
                    "aqi": int(pm25 * 1.5),
                    "timestamp": datetime.utcnow()
                })

    logger.info(f"Fetched {len(records)} records")

    # Step 3
    fetch_weather()
    
    # Step 4
    engine = create_engine(os.environ.get("DATABASE_URL"))
    rows_written = 0
    with engine.begin() as conn:
        for r in records:
            try:
                # Upsert station
                station_sql = text("""
                    INSERT INTO stations (name, lat, lon)
                    VALUES (:name, :lat, :lon)
                    ON CONFLICT (name) DO UPDATE SET lat=EXCLUDED.lat, lon=EXCLUDED.lon
                    RETURNING id
                """)
                st_res = conn.execute(station_sql, {"name": r["station_name"], "lat": r["lat"], "lon": r["lon"]})
                station_id = st_res.scalar()

                # Insert reading
                readings_sql = text("""
                    INSERT INTO readings (station_id, timestamp, pm25, pm10, aqi, wind_speed, temperature, humidity)
                    VALUES (:station_id, :timestamp, :pm25, :pm10, :aqi, :wind_speed, :temperature, :humidity)
                    ON CONFLICT DO NOTHING
                """)
                conn.execute(readings_sql, {
                    "station_id": station_id,
                    "timestamp": r["timestamp"],
                    "pm25": r["pm25"],
                    "pm10": r.get("pm10", r["pm25"] * 1.5),
                    "aqi": r["aqi"],
                    "wind_speed": LATEST_WEATHER["wind_speed"],
                    "temperature": LATEST_WEATHER["temperature"],
                    "humidity": LATEST_WEATHER["humidity"]
                })
                rows_written += 1
            except Exception as e:
                logger.error(f"Failed to upsert DB for record {r['station_name']}: {e}")

        # Step 4.5 - Process FIRMS data
        firms_anomalies = fetch_firms_data()
        ward_anomaly_counts = {}
        for anomaly in firms_anomalies:
            try:
                ward_sql = text("SELECT id FROM wards WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) LIMIT 1")
                ward_id = conn.execute(ward_sql, {"lon": anomaly["lon"], "lat": anomaly["lat"]}).scalar()
                if ward_id is not None:
                    ward_anomaly_counts[ward_id] = ward_anomaly_counts.get(ward_id, 0) + 1
            except Exception:
                pass
                
        # Step 5 - Hotspot Detection
        try:
            hotspot_sql = text("""
                SELECT s.name, s.lat, s.lon, r.aqi, r.pm25
                FROM readings r
                JOIN stations s ON r.station_id = s.id
                WHERE r.timestamp > NOW() - INTERVAL '2 hours'
                AND r.aqi > 150
                ORDER BY r.aqi DESC
                LIMIT 10
            """)
            hotspots = conn.execute(hotspot_sql).mappings().all()
            
            insert_hotspot_sql = text("""
                INSERT INTO hotspots (ward_id, geometry, attributed_source, confidence_score, detected_at, thermal_anomaly_count)
                VALUES (
                    :ward_id,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                    'unknown',
                    0.0,
                    NOW(),
                    :anomaly_count
                )
                ON CONFLICT DO NOTHING
            """)
            for h in hotspots:
                ward_sql = text("SELECT id FROM wards WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) LIMIT 1")
                ward_id = conn.execute(ward_sql, {"lon": h["lon"], "lat": h["lat"]}).scalar()
                if ward_id is not None:
                    anomaly_count = ward_anomaly_counts.get(ward_id, 0)
                    conn.execute(insert_hotspot_sql, {"ward_id": ward_id, "lon": h["lon"], "lat": h["lat"], "anomaly_count": anomaly_count})
                    
        except Exception as e:
            logger.error(f"Failed to detect/insert hotspots: {e}")

    logger.info(f"Ingestion finished, {rows_written} rows written to DB")
    
    # TODO: FIRMS integration

if __name__ == "__main__":
    run_ingestion()

"""
repository.py
--------------
Real-DB data access functions for Neon Postgres. Each function returns data
in the exact same shape as the corresponding mock_data.py generator, so
agents/api code doesn't need to change at all when you switch from mock to
real data -- only api/main.py's data source calls need to switch.

All read-only, plain SQL via SQLAlchemy `text()` -- no ORM models needed for
a hackathon timeline, and it keeps queries transparent for debugging.
"""

import pandas as pd
from sqlalchemy import text

from db.database import get_engine


def fetch_hotspot_features(limit: int = 500) -> pd.DataFrame:
    """
    Matches mock_data.generate_hotspot_features() output shape:
    ward, traffic_density_idx, construction_permit_density,
    industrial_stack_count, thermal_anomaly_count, dust_landuse_pct, pm25
    (no source_label -- that's only available for historical labeled data,
    if you have any; otherwise train on a labeled subset separately.)
    """
    query = text("""
        SELECT
            w.name AS ward,
            h.traffic_density_idx,
            h.construction_permit_density,
            h.industrial_stack_count,
            h.thermal_anomaly_count,
            h.dust_landuse_pct,
            h.pm25
        FROM hotspots h
        JOIN wards w ON w.id = h.ward_id
        ORDER BY h.detected_at DESC
        LIMIT :limit
    """)
    with get_engine().connect() as conn:
        return pd.read_sql(query, conn, params={"limit": limit})


def fetch_historical_aqi(city: str = None, days: int = 400) -> pd.DataFrame:
    """
    Matches mock_data.generate_historical_aqi() output shape: ward, date, aqi
    Aggregates readings to a daily average per ward via the station->ward link.
    """
    query = text("""
        SELECT
            w.name AS ward,
            date_trunc('day', r.timestamp)::date AS date,
            avg(r.aqi) AS aqi
        FROM readings r
        JOIN stations s ON s.id = r.station_id
        JOIN wards w ON w.id = s.ward_id
        WHERE r.timestamp >= now() - (:days || ' days')::interval
          AND (:city IS NULL OR w.city = :city)
        GROUP BY w.name, date_trunc('day', r.timestamp)
        ORDER BY w.name, date
    """)
    with get_engine().connect() as conn:
        return pd.read_sql(query, conn, params={"days": days, "city": city})


def fetch_citizen_profile(user_id: str) -> dict | None:
    """Matches mock_data.generate_citizen_profile() output shape."""
    query = text("""
        SELECT c.id AS user_id, w.name AS ward, c.language, c.conditions,
               c.outdoor_worker, c.elderly
        FROM citizens c
        JOIN wards w ON w.id = c.ward_id
        WHERE c.id = :user_id
    """)
    with get_engine().connect() as conn:
        row = conn.execute(query, {"user_id": user_id}).mappings().first()
        return dict(row) if row else None


def fetch_latest_forecast(ward_name: str) -> float | None:
    """Latest predicted AQI for a ward, used to feed the Citizen Advisory Agent."""
    query = text("""
        SELECT f.predicted_aqi
        FROM forecasts f
        JOIN wards w ON w.id = f.ward_id
        WHERE w.name = :ward_name
        ORDER BY f.timestamp_generated DESC
        LIMIT 1
    """)
    with get_engine().connect() as conn:
        row = conn.execute(query, {"ward_name": ward_name}).first()
        return float(row[0]) if row else None


def fetch_active_hotspots_for_map(ward_name: str = None, limit: int = 200) -> pd.DataFrame:
    """
    Hotspots with lat/lon extracted from the PostGIS `geometry` column
    (ST_Y = lat, ST_X = lon) plus attribution results, ready for the
    Leaflet map layer (Feature 6).
    """
    query = text("""
        SELECT
            h.id AS hotspot_id,
            w.name AS ward,
            ST_Y(h.geometry) AS lat,
            ST_X(h.geometry) AS lon,
            h.attributed_source,
            h.confidence_score,
            h.detected_at
        FROM hotspots h
        JOIN wards w ON w.id = h.ward_id
        WHERE (:ward_name IS NULL OR w.name = :ward_name)
        ORDER BY h.detected_at DESC
        LIMIT :limit
    """)
    with get_engine().connect() as conn:
        return pd.read_sql(query, conn, params={"ward_name": ward_name, "limit": limit})


def insert_hotspot_attribution(hotspot_id: int, predicted_source: str, confidence: float) -> None:
    """Writes the Attribution Agent's output back to the hotspots table."""
    query = text("""
        UPDATE hotspots
        SET attributed_source = :source, confidence_score = :confidence
        WHERE id = :hotspot_id
    """)
    with get_engine().begin() as conn:
        conn.execute(query, {"source": predicted_source, "confidence": confidence, "hotspot_id": hotspot_id})


def insert_advisory(ward_name: str, language: str, message: str, risk_level: str) -> None:
    """Logs a dispatched citizen advisory for the audit trail / Section 9 citizen_advisories table."""
    query = text("""
        INSERT INTO citizen_advisories (ward_id, language, message, risk_level)
        SELECT id, :language, :message, :risk_level FROM wards WHERE name = :ward_name
    """)
    with get_engine().begin() as conn:
        conn.execute(query, {"ward_name": ward_name, "language": language, "message": message, "risk_level": risk_level})

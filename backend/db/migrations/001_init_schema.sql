-- 001_init_schema.sql
-- ClearSkies (AirPulse) — Neon Postgres + PostGIS Schema
-- This mirrors the schema already created live on Neon. Kept here for
-- reference/reproducibility -- do NOT re-run this against the existing
-- database (tables already exist). New teammates setting up a fresh Neon
-- project should run this first, then 002_add_attribution_and_citizens.sql.

CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================
-- WARDS
-- ============================
CREATE TABLE wards (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    geometry GEOMETRY(Polygon, 4326) NOT NULL
);
CREATE INDEX idx_wards_geometry ON wards USING GIST (geometry);

-- ============================
-- STATIONS
-- ============================
CREATE TABLE stations (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    location GEOMETRY(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon, lat), 4326)) STORED,
    ward_id INTEGER REFERENCES wards(id),
    source TEXT
);
CREATE INDEX idx_stations_location ON stations USING GIST (location);
CREATE INDEX idx_stations_ward ON stations (ward_id);

-- ============================
-- READINGS (time series)
-- ============================
CREATE TABLE readings (
    id BIGSERIAL PRIMARY KEY,
    station_id INTEGER NOT NULL REFERENCES stations(id),
    timestamp TIMESTAMPTZ NOT NULL,
    pm25 DOUBLE PRECISION,
    pm10 DOUBLE PRECISION,
    no2 DOUBLE PRECISION,
    so2 DOUBLE PRECISION,
    co DOUBLE PRECISION,
    o3 DOUBLE PRECISION,
    aqi INTEGER
);
CREATE INDEX idx_readings_station_time ON readings (station_id, timestamp DESC);

-- ============================
-- FORECASTS
-- ============================
CREATE TABLE forecasts (
    id BIGSERIAL PRIMARY KEY,
    ward_id INTEGER NOT NULL REFERENCES wards(id),
    timestamp_generated TIMESTAMPTZ NOT NULL DEFAULT now(),
    forecast_horizon_hr INTEGER NOT NULL,
    predicted_aqi INTEGER,
    confidence DOUBLE PRECISION
);
CREATE INDEX idx_forecasts_ward_time ON forecasts (ward_id, timestamp_generated DESC);

-- ============================
-- EMISSION SOURCES (registered industries, construction sites, etc.)
-- ============================
CREATE TABLE emission_sources (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL, -- industry / construction / dust / stubble / traffic
    name TEXT,
    geometry GEOMETRY(Geometry, 4326) NOT NULL, -- point or polygon
    permit_status TEXT,
    last_inspected TIMESTAMPTZ
);
CREATE INDEX idx_emission_sources_geometry ON emission_sources USING GIST (geometry);

-- ============================
-- HOTSPOTS
-- ============================
CREATE TABLE hotspots (
    id BIGSERIAL PRIMARY KEY,
    ward_id INTEGER NOT NULL REFERENCES wards(id),
    geometry GEOMETRY(Geometry, 4326) NOT NULL, -- point or polygon
    attributed_source TEXT, -- traffic / construction / industrial / stubble-burning / dust
    confidence_score DOUBLE PRECISION,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_hotspots_geometry ON hotspots USING GIST (geometry);
CREATE INDEX idx_hotspots_ward ON hotspots (ward_id);

-- ============================
-- ENFORCEMENT QUEUE
-- ============================
CREATE TABLE enforcement_queue (
    id BIGSERIAL PRIMARY KEY,
    hotspot_id BIGINT NOT NULL REFERENCES hotspots(id),
    emission_source_id INTEGER REFERENCES emission_sources(id),
    priority_score DOUBLE PRECISION,
    status TEXT DEFAULT 'pending', -- pending / assigned / resolved
    assigned_to TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_enforcement_status ON enforcement_queue (status);

-- ============================
-- INTERVENTIONS (outcome tracking / feedback loop)
-- ============================
CREATE TABLE interventions (
    id BIGSERIAL PRIMARY KEY,
    enforcement_queue_id BIGINT NOT NULL REFERENCES enforcement_queue(id),
    action_taken TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    aqi_before INTEGER,
    aqi_after INTEGER
);

-- ============================
-- CITIZEN ADVISORIES
-- ============================
CREATE TABLE citizen_advisories (
    id BIGSERIAL PRIMARY KEY,
    ward_id INTEGER NOT NULL REFERENCES wards(id),
    language TEXT NOT NULL,
    message TEXT NOT NULL,
    risk_level TEXT, -- low / moderate / high / severe
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_advisories_ward ON citizen_advisories (ward_id);

-- 003_add_constraints_and_weather.sql
-- Adds UNIQUE constraints needed for ON CONFLICT upserts, and
-- weather columns to readings that the ingestion pipeline writes.

-- ========== UNIQUE constraints for upsert support ==========
-- seed.py and ingestion.py both use ON CONFLICT (name) which
-- requires a UNIQUE constraint or index on the column.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'wards_name_unique'
    ) THEN
        ALTER TABLE wards ADD CONSTRAINT wards_name_unique UNIQUE (name);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'stations_name_unique'
    ) THEN
        ALTER TABLE stations ADD CONSTRAINT stations_name_unique UNIQUE (name);
    END IF;
END $$;

-- ========== Weather columns on readings ==========
-- The ingestion pipeline attaches Open-Meteo weather data to every
-- reading row; the original schema didn't include these.

ALTER TABLE readings ADD COLUMN IF NOT EXISTS wind_speed DOUBLE PRECISION;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS temperature DOUBLE PRECISION;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS humidity DOUBLE PRECISION;

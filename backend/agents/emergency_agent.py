"""
emergency_agent.py
--------------------
System Feature 11: Emergency Pollution Detection

MERGE NOTE: two independent versions of this agent were built in parallel
-- one keyed on individual stations with a rolling z-score check, one
keyed on wards with a rate-of-change + absolute-threshold check. The
ward-keyed version doesn't match the actual schema (`readings` has a
station_id FK, not a ward_id -- see migrations/001_init_schema.sql), so
this file keeps the station-level foundation but runs all three trigger
conditions together, since they catch genuinely different failure modes:

  1. Rolling z-score on PM2.5: catches a spike that's abnormal relative to
     THAT station's own recent baseline, even if the absolute AQI isn't
     severe yet (useful for stations with different normal baselines).
  2. Rate-of-change on AQI: catches a fast-onset event within a short
     window regardless of whether it's "statistically surprising" yet.
  3. Absolute severe-band threshold: catches sustained severe pollution
     even if it built up gradually and neither of the above ever fired.

Any one condition is enough to raise an alert; if more than one fires,
the alert reports all of them so officials can see why it was flagged.

Role: Detects sudden or sustained abnormal pollution conditions per
      station, combining statistical and rule-based triggers.
Inputs: per-station reading series (station_id, timestamp, pm25, aqi).
Outputs: EmergencyAlert if any trigger condition fires, else None.
Talks to: Notification Service (push/SMS/IVR dispatch), Enforcement Queue
          (unexplained/high-priority spikes get flagged), Recommendation
          Agent (can request an emergency-tier action set).
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

import pandas as pd
import numpy as np

SEVERE_AQI_THRESHOLD = 400
RATE_OF_CHANGE_THRESHOLD = 100  # AQI points
RATE_OF_CHANGE_WINDOW_MIN = 45  # within this many minutes
ZSCORE_THRESHOLD = 3.0
ZSCORE_ROLLING_WINDOW_HOURS = 24


@dataclass
class EmergencyAlert:
    station_id: int
    timestamp: str
    pm25: float
    aqi: Optional[float]
    zscore: Optional[float]
    aqi_delta: Optional[float]
    window_minutes: Optional[int]
    trigger_types: list  # e.g. ["statistical_spike"], ["rate_of_change", "absolute_threshold"]
    priority: str  # "high" | "critical"
    message: str


class EmergencyDetectionAgent:
    """
    Role: Runs three independent trigger checks (rolling z-score,
          rate-of-change, absolute severe threshold) on each station's
          recent readings and raises a combined alert if any fire.
    Inputs: per-station reading series (station_id, timestamp, pm25, aqi).
    Outputs: EmergencyAlert or None.
    Talks to: Notification Service, Enforcement Queue.
    """

    def __init__(
        self,
        zscore_threshold: float = ZSCORE_THRESHOLD,
        zscore_window_hours: int = ZSCORE_ROLLING_WINDOW_HOURS,
        severe_aqi_threshold: float = SEVERE_AQI_THRESHOLD,
        rate_threshold: float = RATE_OF_CHANGE_THRESHOLD,
        rate_window_min: int = RATE_OF_CHANGE_WINDOW_MIN,
    ):
        self.zscore_threshold = zscore_threshold
        self.zscore_window_hours = zscore_window_hours
        self.severe_aqi_threshold = severe_aqi_threshold
        self.rate_threshold = rate_threshold
        self.rate_window_min = rate_window_min

    def check_station(self, reading_series: pd.DataFrame) -> Optional[EmergencyAlert]:
        """reading_series: DataFrame with [station_id, timestamp, pm25, aqi], any order."""
        if reading_series.empty or len(reading_series) < 3:
            return None

        df = reading_series.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        latest = df.iloc[-1]
        station_id = int(latest["station_id"])
        current_time = latest["timestamp"]
        pm25 = float(latest["pm25"])
        aqi = float(latest["aqi"]) if "aqi" in df.columns and not pd.isna(latest.get("aqi")) else None

        triggers = []
        zscore_val = None
        aqi_delta = None
        window_minutes = None

        # --- Trigger 1: rolling z-score on PM2.5 ---
        ts_indexed = df.set_index("timestamp")
        window = f"{self.zscore_window_hours}h"
        rolling_mean = ts_indexed["pm25"].rolling(window).mean()
        rolling_std = ts_indexed["pm25"].rolling(window).std()
        zscore_series = (ts_indexed["pm25"] - rolling_mean) / rolling_std.replace(0, np.nan)
        latest_z = zscore_series.iloc[-1]
        if not pd.isna(latest_z) and abs(latest_z) >= self.zscore_threshold:
            triggers.append("statistical_spike")
            zscore_val = round(float(latest_z), 2)

        # --- Trigger 2: rate-of-change on AQI within a short window ---
        if aqi is not None:
            window_start = current_time - timedelta(minutes=self.rate_window_min)
            window_df = df[df["timestamp"] >= window_start]
            if not window_df.empty and "aqi" in window_df.columns:
                earliest_in_window = window_df.iloc[0]
                delta = aqi - float(earliest_in_window["aqi"])
                elapsed_min = (current_time - earliest_in_window["timestamp"]).total_seconds() / 60
                if delta >= self.rate_threshold and elapsed_min <= self.rate_window_min:
                    triggers.append("rate_of_change")
                    aqi_delta = round(delta, 1)
                    window_minutes = int(elapsed_min)

        # --- Trigger 3: absolute severe-band threshold ---
        if aqi is not None and aqi >= self.severe_aqi_threshold:
            triggers.append("absolute_threshold")

        if not triggers:
            return None

        priority = "critical" if len(triggers) > 1 or "absolute_threshold" in triggers else "high"
        message = self._build_message(station_id, triggers, pm25, aqi, zscore_val, aqi_delta, window_minutes)

        return EmergencyAlert(
            station_id=station_id,
            timestamp=str(current_time),
            pm25=pm25,
            aqi=aqi,
            zscore=zscore_val,
            aqi_delta=aqi_delta,
            window_minutes=window_minutes,
            trigger_types=triggers,
            priority=priority,
            message=message,
        )

    def check_all_stations(self, readings_by_station: dict) -> list:
        """readings_by_station: {station_id: reading_series DataFrame}"""
        alerts = []
        for station_id, series in readings_by_station.items():
            alert = self.check_station(series)
            if alert is not None:
                alerts.append(alert)
        return alerts

    @staticmethod
    def _build_message(station_id, triggers, pm25, aqi, zscore_val, aqi_delta, window_minutes) -> str:
        parts = [f"EMERGENCY at station {station_id}:"]
        if "statistical_spike" in triggers:
            parts.append(f"PM2.5 is a statistical outlier vs. this station's own baseline (z={zscore_val:.1f}).")
        if "rate_of_change" in triggers:
            parts.append(f"AQI rose {aqi_delta:.0f} points in {window_minutes} min -- fast-onset event.")
        if "absolute_threshold" in triggers:
            parts.append(f"AQI has reached {aqi:.0f}, in the severe band.")
        parts.append(
            "Cross-check against NASA FIRMS fire data to see if it's fire/stubble-burning "
            "related, otherwise flag for immediate inspection."
        )
        return " ".join(parts)


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.mock_data import generate_station_reading_series

    agent = EmergencyDetectionAgent()

    print("--- Station with a spike ---")
    spike_series = generate_station_reading_series(station_id=1, spike=True)
    print(agent.check_station(spike_series))

    print("\n--- Station with no spike ---")
    normal_series = generate_station_reading_series(station_id=2, spike=False)
    print(agent.check_station(normal_series))  # should be None
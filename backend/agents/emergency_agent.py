"""
emergency_agent.py
---------------------
System Feature 11: Emergency Pollution Detection

Detects sudden, fast-onset AQI spikes (industrial upset, uncontrolled
burning, accident) within minutes -- distinct from the Trend Analysis
Agent's daily-level anomaly detection, which looks for unusual *days* in
historical data, not unusual *minutes* in a live stream.

Two independent triggers, either of which fires an emergency:
  1. Rate-of-change: AQI rises faster than a defined threshold within a
     short rolling window (catches fast-onset events regardless of
     absolute level).
  2. Absolute threshold breach: AQI crosses into the "severe" band
     regardless of how fast it got there (catches sustained severe
     conditions that a rate check alone might miss).
"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

import pandas as pd

SEVERE_THRESHOLD = 400
RATE_OF_CHANGE_THRESHOLD = 100  # AQI points
RATE_OF_CHANGE_WINDOW_MIN = 45  # within this many minutes


@dataclass
class EmergencyAlert:
    ward: str
    triggered_at: str
    trigger_type: str  # "rate_of_change" | "absolute_threshold" | "both"
    current_aqi: float
    aqi_delta: Optional[float]
    window_minutes: Optional[int]
    message: str


class EmergencyDetectionAgent:
    """
    Role: Detects sudden pollution spikes in near-real-time and triggers
          immediate alerts, bypassing the normal daily forecast/attribution
          cycle for speed.
    Inputs: sub-hourly AQI readings stream for a ward/station.
    Outputs: EmergencyAlert if a trigger condition fires, else None.
    Talks to: Notification Service (immediate dispatch), Recommendation
              Agent (can request an emergency-tier action set).
    """

    def __init__(
        self,
        severe_threshold: float = SEVERE_THRESHOLD,
        rate_threshold: float = RATE_OF_CHANGE_THRESHOLD,
        rate_window_min: int = RATE_OF_CHANGE_WINDOW_MIN,
    ):
        self.severe_threshold = severe_threshold
        self.rate_threshold = rate_threshold
        self.rate_window_min = rate_window_min

    def check(self, readings_df: pd.DataFrame) -> Optional[EmergencyAlert]:
        """
        readings_df: columns [ward, timestamp, aqi], sorted or unsorted,
        covering at least the last `rate_window_min` minutes for one ward.
        """
        if readings_df.empty:
            return None

        df = readings_df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        ward = df["ward"].iloc[-1]
        latest = df.iloc[-1]
        current_aqi = float(latest["aqi"])
        current_time = latest["timestamp"]

        # rate-of-change check: compare current reading to the earliest
        # reading within the rolling window
        window_start = current_time - timedelta(minutes=self.rate_window_min)
        window_df = df[df["timestamp"] >= window_start]
        earliest_in_window = window_df.iloc[0]
        aqi_delta = current_aqi - float(earliest_in_window["aqi"])
        elapsed_min = (current_time - earliest_in_window["timestamp"]).total_seconds() / 60

        rate_triggered = aqi_delta >= self.rate_threshold and elapsed_min <= self.rate_window_min
        absolute_triggered = current_aqi >= self.severe_threshold

        if not rate_triggered and not absolute_triggered:
            return None

        if rate_triggered and absolute_triggered:
            trigger_type = "both"
            message = (
                f"EMERGENCY: {ward} AQI jumped {aqi_delta:.0f} points in "
                f"{elapsed_min:.0f} min and has crossed the severe threshold "
                f"({current_aqi:.0f}). Immediate investigation required."
            )
        elif rate_triggered:
            trigger_type = "rate_of_change"
            message = (
                f"EMERGENCY: {ward} AQI rose {aqi_delta:.0f} points in "
                f"{elapsed_min:.0f} minutes -- fast-onset event detected "
                f"(current: {current_aqi:.0f})."
            )
        else:
            trigger_type = "absolute_threshold"
            message = (
                f"EMERGENCY: {ward} AQI has reached {current_aqi:.0f}, in the "
                f"severe band. Immediate public health advisory recommended."
            )

        return EmergencyAlert(
            ward=ward,
            triggered_at=str(current_time),
            trigger_type=trigger_type,
            current_aqi=current_aqi,
            aqi_delta=round(aqi_delta, 1) if rate_triggered else None,
            window_minutes=int(elapsed_min) if rate_triggered else None,
            message=message,
        )

    def check_all_wards(self, readings_by_ward: dict) -> list[EmergencyAlert]:
        """readings_by_ward: {ward_name: readings_df}"""
        alerts = []
        for ward, df in readings_by_ward.items():
            alert = self.check(df)
            if alert:
                alerts.append(alert)
        return alerts


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.mock_data import generate_realtime_readings

    agent = EmergencyDetectionAgent()

    print("--- Ward with a spike ---")
    spike_readings = generate_realtime_readings("Ward-5", spike=True)
    alert = agent.check(spike_readings)
    print(alert)

    print("\n--- Ward with no spike ---")
    normal_readings = generate_realtime_readings("Ward-6", spike=False)
    alert = agent.check(normal_readings)
    print(alert)  # should be None

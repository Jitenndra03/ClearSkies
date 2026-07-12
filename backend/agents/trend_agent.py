"""
trend_agent.py
---------------
System Feature 10: Trend Analysis

Mines historical AQI time series for:
  - seasonal patterns (winter pollution bump, etc.)
  - day-of-week effects (weekday traffic vs. weekend)
  - festival-linked spikes (Diwali, harvest/stubble season, etc.)

Outputs feed the Analytics dashboard and give the Recommendation Agent
context like "this ward always spikes during Diwali week -- pre-position
enforcement now" instead of reacting after the fact.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd


@dataclass
class TrendReport:
    ward: str
    avg_aqi: float
    weekday_avg: float
    weekend_avg: float
    weekday_vs_weekend_delta: float
    monthly_avg: dict
    peak_month: str
    festival_spikes: list = field(default_factory=list)
    anomaly_days: list = field(default_factory=list)


class TrendAnalysisAgent:
    """
    Role: Mines historical AQI data for seasonal, weekly, and event-linked
          patterns.
    Inputs: daily AQI time series per ward (date, ward, aqi).
    Outputs: TrendReport per ward (dashboard-ready summary stats + flagged
             anomaly days).
    Talks to: Analytics Dashboard (consumes TrendReport), Recommendation
              Agent (uses festival_spikes to pre-position interventions
              ahead of known high-risk windows).
    """

    def __init__(self, anomaly_std_threshold: float = 2.0):
        self.anomaly_std_threshold = anomaly_std_threshold

    def analyze_ward(self, df: pd.DataFrame, ward: str, festival_calendar: dict = None) -> TrendReport:
        ward_df = df[df["ward"] == ward].copy()
        ward_df["date"] = pd.to_datetime(ward_df["date"])
        ward_df["weekday"] = ward_df["date"].dt.weekday  # 0=Mon ... 6=Sun
        ward_df["month"] = ward_df["date"].dt.month_name()

        avg_aqi = round(ward_df["aqi"].mean(), 1)

        weekday_avg = round(ward_df[ward_df["weekday"] < 5]["aqi"].mean(), 1)
        weekend_avg = round(ward_df[ward_df["weekday"] >= 5]["aqi"].mean(), 1)

        monthly_avg = ward_df.groupby("month")["aqi"].mean().round(1).to_dict()
        peak_month = max(monthly_avg, key=monthly_avg.get) if monthly_avg else "unknown"

        # anomaly detection: days where AQI deviates > N std devs from the
        # ward's rolling 30-day mean -- catches sudden spikes regardless of cause
        ward_df = ward_df.sort_values("date")
        ward_df["rolling_mean"] = ward_df["aqi"].rolling(window=30, min_periods=7).mean()
        ward_df["rolling_std"] = ward_df["aqi"].rolling(window=30, min_periods=7).std()
        ward_df["z_score"] = (ward_df["aqi"] - ward_df["rolling_mean"]) / ward_df["rolling_std"]
        anomalies = ward_df[ward_df["z_score"].abs() > self.anomaly_std_threshold]
        anomaly_days = [
            {"date": str(row["date"].date()), "aqi": row["aqi"], "z_score": round(row["z_score"], 2)}
            for _, row in anomalies.iterrows()
        ]

        festival_spikes = self._detect_festival_spikes(ward_df, festival_calendar or {})

        return TrendReport(
            ward=ward,
            avg_aqi=avg_aqi,
            weekday_avg=weekday_avg,
            weekend_avg=weekend_avg,
            weekday_vs_weekend_delta=round(weekday_avg - weekend_avg, 1),
            monthly_avg=monthly_avg,
            peak_month=peak_month,
            festival_spikes=festival_spikes,
            anomaly_days=anomaly_days,
        )

    def analyze_all_wards(self, df: pd.DataFrame, festival_calendar: dict = None) -> dict:
        return {ward: self.analyze_ward(df, ward, festival_calendar) for ward in df["ward"].unique()}

    @staticmethod
    def _detect_festival_spikes(ward_df: pd.DataFrame, festival_calendar: dict, window_days: int = 3) -> list:
        """
        For each known festival/event date, compares the average AQI in the
        window around it to the ward's baseline (30-day rolling mean just
        before the window) and flags it as a spike if elevated meaningfully.
        """
        spikes = []
        for name, fdate in festival_calendar.items():
            fdate = pd.Timestamp(fdate)
            window_mask = (ward_df["date"] >= fdate - timedelta(days=0)) & (
                ward_df["date"] <= fdate + timedelta(days=window_days)
            )
            baseline_mask = (ward_df["date"] >= fdate - timedelta(days=30)) & (
                ward_df["date"] < fdate
            )

            window_avg = ward_df[window_mask]["aqi"].mean()
            baseline_avg = ward_df[baseline_mask]["aqi"].mean()

            if pd.notna(window_avg) and pd.notna(baseline_avg) and baseline_avg > 0:
                pct_increase = round(((window_avg - baseline_avg) / baseline_avg) * 100, 1)
                if pct_increase > 15:  # meaningful spike threshold
                    spikes.append({
                        "event": name,
                        "date": str(fdate.date()),
                        "baseline_aqi": round(baseline_avg, 1),
                        "event_window_aqi": round(window_avg, 1),
                        "pct_increase": pct_increase,
                    })
        return spikes


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.mock_data import generate_historical_aqi, FESTIVALS_2025_26

    df = generate_historical_aqi()
    agent = TrendAnalysisAgent()
    report = agent.analyze_ward(df, "Ward-1", FESTIVALS_2025_26)
    print(report)

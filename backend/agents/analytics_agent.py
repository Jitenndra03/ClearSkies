"""
analytics_agent.py
--------------------
System Feature 12: Analytics Dashboard

Aggregates data that already exists across other agents/tables into the
three views Section 11 of the plan calls for on the Admin Panel's
"wow" screen: enforcement queue status breakdown, intervention ROI over
time, and hotspot source-category trends. This agent doesn't compute
anything new -- it's a read-only reporting layer, same spirit as
MultiCityComparisonAgent (Feature 10), just scoped to one city/ward
instead of comparing across cities.

Role: Aggregates enforcement/intervention/hotspot data into dashboard-
      ready summaries.
Inputs: enforcement queue snapshot, intervention history, hotspot source
        breakdown -- each as a DataFrame.
Outputs: AnalyticsSummary.
Talks to: Analytics Dashboard UI (Admin Panel).
"""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class AnalyticsSummary:
    enforcement_status_counts: dict = field(default_factory=dict)   # {status: count}
    total_interventions: int = 0
    avg_aqi_drop: float = 0.0
    best_action_type: str = ""          # action type with highest avg AQI drop
    intervention_roi_by_date: list = field(default_factory=list)     # [{date, avg_aqi_drop, count}]
    source_trend: dict = field(default_factory=dict)                 # {source: count}


class AnalyticsAgent:
    """
    Role: Rolls up enforcement queue status, intervention outcomes, and
          hotspot source trends into one dashboard-ready summary.
    Inputs: enforcement_df (id, ward, status, priority_score),
            interventions_df (date, ward, action_taken, aqi_before, aqi_after),
            source_df (attributed_source, count) -- ward- or city-scoped.
    Outputs: AnalyticsSummary.
    Talks to: Analytics Dashboard UI.
    """

    def summarize(
        self,
        enforcement_df: pd.DataFrame,
        interventions_df: pd.DataFrame,
        source_df: pd.DataFrame = None,
    ) -> AnalyticsSummary:
        status_counts = (
            enforcement_df["status"].value_counts().to_dict() if not enforcement_df.empty else {}
        )

        total_interventions = len(interventions_df)
        avg_drop = 0.0
        best_action = ""
        roi_by_date = []

        if not interventions_df.empty:
            df = interventions_df.copy()
            df["aqi_drop"] = df["aqi_before"] - df["aqi_after"]
            avg_drop = round(float(df["aqi_drop"].mean()), 1)

            by_action = df.groupby("action_taken")["aqi_drop"].mean().sort_values(ascending=False)
            if not by_action.empty:
                best_action = by_action.index[0]

            by_date = df.groupby("date")["aqi_drop"].agg(["mean", "count"]).reset_index()
            roi_by_date = [
                {"date": str(row["date"]), "avg_aqi_drop": round(float(row["mean"]), 1), "count": int(row["count"])}
                for _, row in by_date.iterrows()
            ]

        source_trend = {}
        if source_df is not None and not source_df.empty:
            group_col = "attributed_source"
            count_col = "count" if "count" in source_df.columns else None
            if count_col:
                source_trend = source_df.groupby(group_col)[count_col].sum().to_dict()
            else:
                source_trend = source_df[group_col].value_counts().to_dict()

        return AnalyticsSummary(
            enforcement_status_counts=status_counts,
            total_interventions=total_interventions,
            avg_aqi_drop=avg_drop,
            best_action_type=best_action,
            intervention_roi_by_date=roi_by_date,
            source_trend=source_trend,
        )


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.mock_data import (
        generate_enforcement_queue_snapshot, generate_intervention_roi_series,
        generate_source_breakdown_by_city,
    )

    enforcement_df = generate_enforcement_queue_snapshot()
    interventions_df = generate_intervention_roi_series(days=30)
    source_df = generate_source_breakdown_by_city()

    agent = AnalyticsAgent()
    summary = agent.summarize(enforcement_df, interventions_df, source_df)
    print("Enforcement status counts:", summary.enforcement_status_counts)
    print("Total interventions:", summary.total_interventions)
    print("Avg AQI drop:", summary.avg_aqi_drop)
    print("Best action type:", summary.best_action_type)
    print("ROI by date (first 3):", summary.intervention_roi_by_date[:3])
    print("Source trend:", summary.source_trend)
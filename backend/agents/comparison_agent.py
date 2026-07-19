"""
comparison_agent.py
---------------------
System Feature 10: Multi-city Comparison

NOTE ON NUMBERING: an earlier commit's `trend_agent.py` was labeled
"Feature 10" in its docstring/README -- per the original ClearSkies plan
(Section 2), that agent is actually Feature 7 (Trend Analysis). This file
is the real Feature 10: Multi-city Comparison, benchmarking intervention
effectiveness across cities rather than mining one city's history. Worth
a quick heads-up to your teammate so the README labels get fixed too.

Role: Benchmarks AQI levels, intervention counts, and enforcement
      effectiveness across multiple cities.
Inputs: daily AQI history per city + logged interventions + hotspot
        source breakdown per city.
Outputs: ComparisonReport per city + a ranked list.
Talks to: Analytics Dashboard (city comparison view).
"""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class CityComparisonEntry:
    city: str
    avg_aqi: float
    intervention_count: int
    avg_aqi_drop_per_intervention: float
    source_breakdown: dict = field(default_factory=dict)


class MultiCityComparisonAgent:
    """
    Role: Aggregates and ranks cities by AQI level and intervention
          effectiveness -- a read-only reporting agent, not a live
          pipeline stage.
    Inputs: history_df (city, date, aqi, intervention_logged, aqi_drop),
            source_df (city, attributed_source, count).
    Outputs: list[CityComparisonEntry], ranked best-to-worst.
    Talks to: Analytics Dashboard.
    """

    def compare(self, history_df: pd.DataFrame, source_df: pd.DataFrame = None) -> list[CityComparisonEntry]:
        entries = []
        for city, city_df in history_df.groupby("city"):
            avg_aqi = round(float(city_df["aqi"].mean()), 1)

            interventions = city_df[city_df.get("intervention_logged", False) == True]
            intervention_count = int(len(interventions))
            avg_drop = (
                round(float(interventions["aqi_drop"].mean()), 1)
                if intervention_count > 0 else 0.0
            )

            breakdown = {}
            if source_df is not None:
                city_sources = source_df[source_df["city"] == city]
                breakdown = dict(zip(city_sources["attributed_source"], city_sources["count"]))

            entries.append(CityComparisonEntry(
                city=city,
                avg_aqi=avg_aqi,
                intervention_count=intervention_count,
                avg_aqi_drop_per_intervention=avg_drop,
                source_breakdown=breakdown,
            ))

        # Lower avg AQI and higher avg-drop-per-intervention = better performing.
        return sorted(entries, key=lambda e: (e.avg_aqi, -e.avg_aqi_drop_per_intervention))


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.mock_data import generate_multi_city_history, generate_source_breakdown_by_city

    history = generate_multi_city_history()
    sources = generate_source_breakdown_by_city()
    agent = MultiCityComparisonAgent()

    for entry in agent.compare(history, sources):
        print(entry)

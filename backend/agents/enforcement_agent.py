"""
enforcement_agent.py
----------------------
System Feature 4: Smart Enforcement Prioritization

Ranks known/registered emission sources (industries, construction sites,
waste-burning sites, diesel depots) by a composite priority score so
inspectors go where impact is highest -- instead of round-robin or
complaint-driven inspection, which the problem statement identifies as
the current failure mode.

Priority score combines:
  - proximity to an active, high-confidence hotspot
  - permit status (unregistered/expired sites score higher -- more risk)
  - time since last inspection (longer gap -> higher priority)
  - forecast severity for the ward the source sits in

This produces rows ready to insert into the enforcement_queue table.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

PERMIT_RISK_WEIGHT = {
    "unregistered": 1.0,
    "expired": 0.7,
    "valid": 0.2,
}

SEVERITY_WEIGHT = {
    "satisfactory": 0.1,
    "moderate": 0.3,
    "poor": 0.6,
    "very_poor": 0.85,
    "severe": 1.0,
}


@dataclass
class PrioritizedSource:
    source_id: int
    name: str
    ward: str
    type: str
    priority_score: float
    reasons: list


class EnforcementPrioritizationAgent:
    """
    Role: Ranks emission sources by real-time composite risk score.
    Inputs: emission_sources (permit status, last inspection date,
            distance to nearest hotspot) + hotspot attribution confidence
            + ward forecast severity.
    Outputs: ranked list of PrioritizedSource (feeds enforcement_queue).
    Talks to: Recommendation Agent (consumes actions tagged for
              inspector roles), Admin Panel (displays the ranked queue).
    """

    def __init__(
        self,
        w_proximity: float = 0.35,
        w_permit: float = 0.25,
        w_inspection_gap: float = 0.15,
        w_severity: float = 0.25,
    ):
        self.w_proximity = w_proximity
        self.w_permit = w_permit
        self.w_inspection_gap = w_inspection_gap
        self.w_severity = w_severity

    def _proximity_score(self, distance_km: float) -> float:
        # closer sources score higher; decays to ~0 by 3km
        return max(0.0, 1 - (distance_km / 3.0))

    def _inspection_gap_score(self, days_since: int) -> float:
        # normalize against a 1-year cap
        return min(1.0, days_since / 365)

    def score_source(
        self,
        row: pd.Series,
        ward_severity: str,
        hotspot_confidence: Optional[float] = None,
    ) -> PrioritizedSource:
        proximity = self._proximity_score(row["distance_to_nearest_hotspot_km"])
        permit_risk = PERMIT_RISK_WEIGHT.get(row["permit_status"], 0.5)
        inspection_gap = self._inspection_gap_score(row["days_since_last_inspection"])
        severity = SEVERITY_WEIGHT.get(ward_severity, 0.5)

        # optionally down-weight proximity contribution if we're not
        # confident the hotspot near this source is actually the cause
        if hotspot_confidence is not None:
            proximity *= hotspot_confidence

        score = (
            self.w_proximity * proximity
            + self.w_permit * permit_risk
            + self.w_inspection_gap * inspection_gap
            + self.w_severity * severity
        )

        reasons = []
        if proximity > 0.5:
            reasons.append(f"{row['distance_to_nearest_hotspot_km']}km from an active hotspot")
        if row["permit_status"] != "valid":
            reasons.append(f"permit status: {row['permit_status']}")
        if row["days_since_last_inspection"] > 90:
            reasons.append(f"not inspected in {row['days_since_last_inspection']} days")
        if ward_severity in ("very_poor", "severe"):
            reasons.append(f"ward forecast severity: {ward_severity}")

        return PrioritizedSource(
            source_id=int(row["id"]),
            name=row["name"],
            ward=row["ward"],
            type=row["type"],
            priority_score=round(score, 3),
            reasons=reasons,
        )

    def prioritize(
        self,
        sources_df: pd.DataFrame,
        ward_severity_map: dict,
        hotspot_confidence_map: Optional[dict] = None,
    ) -> list[PrioritizedSource]:
        """
        ward_severity_map: {ward_name: severity_band}
        hotspot_confidence_map: optional {ward_name: confidence} from the
                                 Attribution Agent, to weight proximity by
                                 how sure we are the hotspot near this
                                 source is actually the cause.
        """
        results = []
        for _, row in sources_df.iterrows():
            severity = ward_severity_map.get(row["ward"], "moderate")
            confidence = (hotspot_confidence_map or {}).get(row["ward"])
            results.append(self.score_source(row, severity, confidence))

        results.sort(key=lambda x: x.priority_score, reverse=True)
        return results


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.mock_data import generate_emission_sources

    sources = generate_emission_sources()
    agent = EnforcementPrioritizationAgent()

    severity_map = {"Ward-1": "very_poor", "Ward-2": "severe", "Ward-3": "moderate",
                     "Ward-4": "poor", "Ward-5": "satisfactory", "Ward-6": "severe",
                     "Ward-7": "poor", "Ward-8": "very_poor"}

    ranked = agent.prioritize(sources, severity_map)
    print("Top 5 priority inspection targets:")
    for r in ranked[:5]:
        print(r)

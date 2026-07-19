"""
heatmap_agent.py
-----------------
System Feature 6: Geospatial Heatmaps

Interpolates point station readings (lat/lon/AQI) into a continuous grid
using Inverse Distance Weighting (IDW) -- closer stations count more, no
variogram fitting needed, runs in milliseconds. Feeds the frontend's
leaflet.heat layer directly.

Role: Turns sparse station points into a dense grid the map can render as
      a heatmap.
Inputs: latest station snapshot (station_id, ward, lat, lon, pm25, aqi).
Outputs: HeatmapGrid (list of {lat, lon, value} points).
Talks to: Dashboard / Map UI (consumes the grid for leaflet.heat).
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class HeatmapGrid:
    city: str
    pollutant: str
    grid: list = field(default_factory=list)   # [{lat, lon, value}, ...]
    stations: list = field(default_factory=list)  # original station points, for markers


class HeatmapAgent:
    """
    Role: Interpolates sparse station readings into a dense AQI/pollutant
          grid for map rendering.
    Inputs: station snapshot DataFrame (station_id, ward, lat, lon, pm25, aqi).
    Outputs: HeatmapGrid.
    Talks to: Map/Dashboard UI (leaflet.heat), Overlay endpoints (roads,
              construction, industrial, fires -- served separately, not
              interpolated).
    """

    def __init__(self, grid_resolution: int = 40, power: float = 2.0):
        self.grid_resolution = grid_resolution
        self.power = power

    def interpolate(
        self,
        station_df: pd.DataFrame,
        city: str,
        pollutant: str = "aqi",
        bbox: dict = None,
    ) -> HeatmapGrid:
        if station_df.empty:
            return HeatmapGrid(city=city, pollutant=pollutant, grid=[], stations=[])

        bbox = bbox or self._infer_bbox(station_df)
        lats = np.linspace(bbox["south"], bbox["north"], self.grid_resolution)
        lons = np.linspace(bbox["west"], bbox["east"], self.grid_resolution)

        sp_lat = station_df["lat"].to_numpy()
        sp_lon = station_df["lon"].to_numpy()
        sp_val = station_df[pollutant].to_numpy()

        grid_points = []
        for lat in lats:
            for lon in lons:
                dist = np.sqrt((sp_lat - lat) ** 2 + (sp_lon - lon) ** 2)
                if np.any(dist < 1e-6):
                    value = float(sp_val[np.argmin(dist)])
                else:
                    weights = 1.0 / (dist ** self.power)
                    value = float(np.sum(weights * sp_val) / np.sum(weights))
                grid_points.append({
                    "lat": round(float(lat), 5),
                    "lon": round(float(lon), 5),
                    "value": round(value, 1),
                })

        stations = station_df[["station_id", "ward", "lat", "lon", pollutant]].to_dict("records")
        return HeatmapGrid(city=city, pollutant=pollutant, grid=grid_points, stations=stations)

    @staticmethod
    def _infer_bbox(station_df: pd.DataFrame, padding: float = 0.02) -> dict:
        """Falls back to a bbox derived from the station points themselves
        if none is supplied -- avoids hardcoding a city's bounds here."""
        return {
            "south": float(station_df["lat"].min() - padding),
            "north": float(station_df["lat"].max() + padding),
            "west": float(station_df["lon"].min() - padding),
            "east": float(station_df["lon"].max() + padding),
        }


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.mock_data import generate_station_snapshot

    df = generate_station_snapshot()
    agent = HeatmapAgent(grid_resolution=10)
    result = agent.interpolate(df, city="Lucknow", pollutant="aqi")
    print(f"Interpolated {len(result.grid)} grid points from {len(result.stations)} stations.")
    print("Sample grid point:", result.grid[0])

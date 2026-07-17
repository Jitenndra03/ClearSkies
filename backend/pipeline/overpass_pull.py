import requests
import geopandas as gpd
from shapely.geometry import shape

def fetch_osm_features(bbox, amenity_type="industrial"):
    """
    bbox format: (south, west, north, east)
    amenity_type: 'industrial', 'construction', or 'highway'
    """
    url = "https://overpass-api.de/api/interpreter"
    
    if amenity_type in ["industrial", "construction"]:
        query = f"""
        [out:json][timeout:25];
        (
          way["landuse"="{amenity_type}"]{bbox};
          relation["landuse"="{amenity_type}"]{bbox};
        );
        out geom;
        """
    elif amenity_type == "highway":
        query = f"""
        [out:json][timeout:25];
        (
          way["highway"~"motorway|trunk|primary|secondary"]{bbox};
        );
        out geom;
        """
    else:
        raise ValueError(
            f"Unknown amenity_type '{amenity_type}' -- expected 'industrial', "
            "'construction', or 'highway'."
        )

    response = requests.post(url, data={'data': query})
        
    response = requests.post(url, data={'data': query})
    if response.status_code != 200:
        raise Exception(f"Overpass API error: {response.status_code}")
        
    data = response.json()
    features = []
    
    for element in data.get('elements', []):
        if 'geometry' in element:
            # Convert Overpass track to LineString or Polygon
            coords = [(pt['lon'], pt['lat']) for pt in element['geometry']]
            if len(coords) >= 2:
                features.append({
                    "type": "Feature",
                    "properties": element.get('tags', {}),
                    "geometry": {"type": "LineString", "coordinates": coords}
                })
                
    gdf = gpd.GeoDataFrame.from_features(features)
    if not gdf.empty:
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf

# Quick cache utility for hackathon
if __name__ == "__main__":
    # Example Bounding box around Kanpur, India
    kanpur_bbox = (26.35, 80.20, 26.55, 80.40) 
    print("Fetching industrial zones...")
    ind_gdf = fetch_osm_features(kanpur_bbox, "industrial")
    ind_gdf.to_file("kanpur_industrial.geojson", driver="GeoJSON")
    print(f"Saved {len(ind_gdf)} industrial features.")
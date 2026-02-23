import requests
import json
import os

def download_and_simplify():
    url = "https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/master/countries.geojson"
    print(f"Downloading from {url}...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error downloading: {e}")
        return

    continents = {} # {continent_name: [polygons]}
    
    for feature in data['features']:
        name = feature['properties'].get('continent', 'Unknown')
        geom = feature['geometry']
        
        if name not in continents:
            continents[name] = []
            
        if geom['type'] == 'Polygon':
            continents[name].append(geom['coordinates'])
        elif geom['type'] == 'MultiPolygon':
            for poly in geom['coordinates']:
                continents[name].append(poly)

    # Simplified data structure: {continent_name: [[[lon, lat], ...], ...]}
    # We'll save it to assets/continents.json
    output_path = r"d:\Vector Infinity\assets\continents.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(continents, f)
    
    print(f"Saved simplified continents to {output_path}")

if __name__ == "__main__":
    download_and_simplify()

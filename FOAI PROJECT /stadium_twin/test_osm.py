import sys; sys.path.insert(0, '.')
from app.geo.osm_fetch import fetch_osm_around
from app.geo.graph_builder import build_graph_from_osm
import logging

logging.basicConfig(level=logging.INFO)

lat, lon = 13.0674, 80.2612 # Rajarathinam
data = fetch_osm_around(lat, lon, 500)
print(f"Fetched {len(data['elements'])} elements")

gdata = build_graph_from_osm(data)
print("Nodes:", len(gdata["graph_json"].get("nodes", [])))
print("Edges:", len(gdata["graph_json"].get("links", [])))

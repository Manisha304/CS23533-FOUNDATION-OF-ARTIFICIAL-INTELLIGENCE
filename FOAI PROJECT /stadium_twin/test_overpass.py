import sys, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.INFO)

from app.geo.osm_fetch import fetch_osm_around
from app.geo.graph_builder import build_graph_from_osm

data = fetch_osm_around(13.0628, 80.2793, 300)
print(f"\nTotal elements: {len(data.get('elements', []))}")

result = build_graph_from_osm(data)
print(f"Graph nodes: {len(result['graph_json'].get('nodes', []))}")
print(f"Graph edges: {len(result['graph_json'].get('links', []))}")
print(f"Polygon points: {len(result['polygon_json'])}")

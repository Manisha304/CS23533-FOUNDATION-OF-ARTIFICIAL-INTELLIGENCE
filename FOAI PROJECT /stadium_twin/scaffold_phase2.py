import os

base_dir = r'c:\Users\manis\OneDrive\Desktop\new foai\stadium_twin'

geocode_py = '''import requests
import time
from functools import lru_cache

# Nominatim strictly requires custom User-Agent and max 1 req/sec
HEADERS = {"User-Agent": "StadiumTwin_v2_Academic_Project/1.0 (manis@example.com)"}
LAST_CALL = 0

@lru_cache(maxsize=100)
def search_location(query: str):
    global LAST_CALL
    now = time.time()
    if now - LAST_CALL < 1.0:
        time.sleep(1.0 - (now - LAST_CALL))
    LAST_CALL = time.time()
    
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 5}
    response = requests.get(url, params=params, headers=HEADERS)
    response.raise_for_status()
    return response.json()
'''

osm_fetch_py = '''import requests
import logging

logger = logging.getLogger(__name__)

def fetch_osm_around(lat: float, lon: float, radius_m: int = 500):
    """
    Fetches OSM elements around a point using Overpass API.
    Looks for the main polygon (stadium/park), paths, roads, and gates.
    """
    # Overpass QL
    query = f"""
    [out:json][timeout:25];
    (
      // The main place (stadium, pitch, park, etc)
      way["leisure"](around:{radius_m},{lat},{lon});
      relation["leisure"](around:{radius_m},{lat},{lon});
      way["building"="stadium"](around:{radius_m},{lat},{lon});
      
      // Paths and roads
      way["highway"~"footway|pedestrian|path|steps|residential|service"](around:{radius_m},{lat},{lon});
      
      // Entrances and exits
      node["entrance"](around:{radius_m},{lat},{lon});
      node["barrier"~"gate|turnstile"](around:{radius_m},{lat},{lon});
      
      // Parking
      way["amenity"="parking"](around:{radius_m},{lat},{lon});
    );
    out body;
    >;
    out skel qt;
    """
    
    url = "https://overpass-api.de/api/interpreter"
    response = requests.post(url, data={"data": query})
    if response.status_code != 200:
        logger.error(f"Overpass API error: {response.text}")
        return {"elements": []}
    
    return response.json()
'''

graph_builder_py = '''import networkx as nx
import math
from typing import Dict, Any

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def build_graph_from_osm(osm_data: dict) -> Dict[str, Any]:
    """
    Takes OSM JSON from Overpass and builds a NetworkX graph.
    Returns a dict with {"graph_json": ..., "polygon_json": ...}
    """
    nodes = {}
    ways = []
    main_polygon = None
    
    for el in osm_data.get("elements", []):
        if el["type"] == "node":
            nodes[el["id"]] = {"lat": el["lat"], "lon": el["lon"], "tags": el.get("tags", {})}
        elif el["type"] == "way":
            ways.append(el)
            
    G = nx.Graph()
    
    # Process ways into graph edges
    for way in ways:
        tags = way.get("tags", {})
        nodes_in_way = way.get("nodes", [])
        
        # Check if it's the main polygon (simple heuristic: largest leisure/building area)
        if "leisure" in tags or "building" in tags:
            if not main_polygon and len(nodes_in_way) > 2 and nodes_in_way[0] == nodes_in_way[-1]:
                # It's a closed ring, assume it's our polygon
                coords = []
                for nid in nodes_in_way:
                    if nid in nodes:
                        coords.append([nodes[nid]["lat"], nodes[nid]["lon"]])
                main_polygon = coords
        
        # If it's a highway/path, add to graph
        if "highway" in tags:
            for i in range(len(nodes_in_way) - 1):
                u, v = nodes_in_way[i], nodes_in_way[i+1]
                if u in nodes and v in nodes:
                    dist = haversine(nodes[u]["lat"], nodes[u]["lon"], nodes[v]["lat"], nodes[v]["lon"])
                    G.add_node(u, lat=nodes[u]["lat"], lon=nodes[u]["lon"], type="junction")
                    G.add_node(v, lat=nodes[v]["lat"], lon=nodes[v]["lon"], type="junction")
                    G.add_edge(u, v, length=dist)
                    
    # Process specific entrance/gate nodes
    for nid, data in nodes.items():
        if "entrance" in data["tags"] or "barrier" in data["tags"]:
            # Make sure it's in the graph, connect to nearest if isolated
            if nid not in G:
                G.add_node(nid, lat=data["lat"], lon=data["lon"], type="gate")
            else:
                G.nodes[nid]["type"] = "gate"
                
    return {
        "graph_json": nx.node_link_data(G),
        "polygon_json": main_polygon or []
    }
'''

api_twin_py = '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .db import get_db
from .models import Twin, User
from .auth import get_current_user
from .geo.osm_fetch import fetch_osm_around
from .geo.graph_builder import build_graph_from_osm

router = APIRouter(prefix="/api/twin", tags=["twin"])

@router.post("/")
def create_twin(name: str, lat: float, lon: float, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    osm_data = fetch_osm_around(lat, lon)
    built_data = build_graph_from_osm(osm_data)
    
    new_twin = Twin(
        name=name,
        lat=lat,
        lon=lon,
        graph_json=built_data["graph_json"],
        polygon_json=built_data["polygon_json"],
        owner_id=current_user.id
    )
    db.add(new_twin)
    db.commit()
    db.refresh(new_twin)
    return new_twin

@router.get("/")
def list_twins(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "admin":
        return db.query(Twin).all()
    return db.query(Twin).filter(Twin.owner_id == current_user.id).all()

@router.get("/{twin_id}")
def get_twin(twin_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    twin = db.query(Twin).filter(Twin.id == twin_id).first()
    if not twin:
        raise HTTPException(status_code=404, detail="Twin not found")
    if twin.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return twin
'''

files = {
    'app/geo/__init__.py': '',
    'app/geo/geocode.py': geocode_py,
    'app/geo/osm_fetch.py': osm_fetch_py,
    'app/geo/graph_builder.py': graph_builder_py,
    'app/api_twin.py': api_twin_py
}

for path, content in files.items():
    full_path = os.path.join(base_dir, path.replace('/', os.sep))
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Phase 2 Python files scaffolded.")

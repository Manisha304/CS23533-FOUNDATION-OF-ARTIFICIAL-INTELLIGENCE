import networkx as nx
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

def build_graph_from_osm(osm_data: dict, center_lat: float, center_lon: float) -> Dict[str, Any]:
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
                    G.add_edge(u, v, length=dist, tags=tags)
    
    # Add synthetic center node for internal paths
    G.add_node("stadium_center", lat=center_lat, lon=center_lon, type="center", label="Center")
    
    # Process specific entrance/gate nodes
    for nid, data in nodes.items():
        if "entrance" in data["tags"] or "barrier" in data["tags"]:
            # Make sure it's in the graph
            if nid not in G:
                G.add_node(nid, lat=data["lat"], lon=data["lon"], type="gate")
                # Connect isolated gate to nearest public road
                nearest = None
                min_dist = float('inf')
                for gn, gdata in G.nodes(data=True):
                    if gn != nid and gn != "stadium_center" and 'lat' in gdata:
                        d = haversine(data["lat"], data["lon"], gdata["lat"], gdata["lon"])
                        if d < min_dist:
                            min_dist = d
                            nearest = gn
                if nearest:
                    G.add_edge(nid, nearest, length=min_dist)
            else:
                G.nodes[nid]["type"] = "gate"
            
            # Connect all OSM gates to the stadium center (creates internal blue paths!)
            dist_to_center = haversine(data["lat"], data["lon"], center_lat, center_lon)
            G.add_edge(nid, "stadium_center", length=dist_to_center)
                
    return {
        "graph_json": nx.node_link_data(G),
        "polygon_json": main_polygon or []
    }

import logging
import requests
from typing import List, Dict, Optional
from .crowd_agents import BDIAgent, haversine
import heapq

logger = logging.getLogger(__name__)

class EmergencyAgent(BDIAgent):
    """
    Emergency Responder Agent.
    Belief: locations and types of nearby responders, incident location/severity.
    Desire: get the right responder to the incident fastest, route public away.
    Intention: compute responder route (vehicle leg + foot leg) and select best hospital.
    """
    def __init__(self, incident_node: str, incident_lat: float, incident_lon: float, severity: str = "high"):
        super().__init__("EmergencyAgent")
        self.beliefs["incident"] = {
            "node": incident_node,
            "lat": incident_lat,
            "lon": incident_lon,
            "severity": severity
        }
        self.beliefs["responders"] = []
        self.desires = ["minimize_response_time", "avoid_crowd_collisions"]

    def update_responders(self, responders: List[Dict]):
        self.beliefs["responders"] = responders
        
    def _get_road_and_foot_nodes(self, graph_json: dict):
        """Identify which nodes in the twin graph are vehicle-accessible vs foot-only."""
        road_nodes = set()
        foot_nodes = set()
        
        nodes_raw = graph_json.get("nodes", [])
        links_raw = graph_json.get("links", [])
        
        # Default all to foot_nodes initially
        node_map = {str(n["id"]): n for n in nodes_raw}
        
        for link in links_raw:
            u, v = str(link["source"]), str(link["target"])
            tags = link.get("tags", {})
            hw = tags.get("highway", "")
            
            # Highways that allow vehicles
            vehicle_friendly = ["primary", "secondary", "tertiary", "residential", "unclassified", "service"]
            
            if any(v_hw in hw for v_hw in vehicle_friendly):
                road_nodes.add(u)
                road_nodes.add(v)
            else:
                foot_nodes.add(u)
                foot_nodes.add(v)
                
        # If no road nodes found (e.g. small twin), fallback: all gates are vehicle accessible
        if not road_nodes:
            for n in nodes_raw:
                if n.get("type") == "gate" or str(n["id"]).startswith("manual_gate"):
                    road_nodes.add(str(n["id"]))
                    
        return road_nodes, node_map, links_raw

    def astar_responder(self, graph_json: dict, start_node: str, goal_node: str, crowd_dense_nodes: set = None) -> dict:
        """
        A* tailored for responders (footpath segment).
        Avoids crowd_dense_nodes unless no alternative.
        """
        if crowd_dense_nodes is None:
            crowd_dense_nodes = set()
            
        road_nodes, node_map, links_raw = self._get_road_and_foot_nodes(graph_json)
        
        adj = {nid: [] for nid in node_map}
        for link in links_raw:
            u, v = str(link["source"]), str(link["target"])
            w = link.get("length", 1.0)
            if u in adj and v in adj:
                adj[u].append((v, w))
                adj[v].append((u, w))
                
        if start_node not in adj or goal_node not in adj:
            return {"path": [], "distance_m": 0}

        pq = [(0.0, start_node)]
        came_from = {start_node: None}
        cost_so_far = {start_node: 0.0}
        
        goal_lat = node_map[goal_node].get("lat")
        goal_lon = node_map[goal_node].get("lon")
        
        found = False
        while pq:
            current_f, current = heapq.heappop(pq)
            if current == goal_node:
                found = True
                break
                
            for neighbor, w in adj[current]:
                # Cost model: penalize crowd dense nodes heavily, but don't block entirely
                penalty = 0.0
                if neighbor in crowd_dense_nodes:
                    penalty = 50.0  # heavy penalty to avoid crowd
                    
                new_cost = cost_so_far[current] + w + penalty
                
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    nb = node_map[neighbor]
                    h = 0
                    if "lat" in nb and goal_lat:
                        h = haversine(nb["lat"], nb["lon"], goal_lat, goal_lon)
                    heapq.heappush(pq, (new_cost + h, neighbor))
                    came_from[neighbor] = current
                    
        if not found:
            return {"path": [], "distance_m": 0}
            
        # Reconstruct
        path_nodes = []
        cur = goal_node
        while cur is not None:
            path_nodes.append(cur)
            cur = came_from.get(cur)
        path_nodes.reverse()
        
        coords = [[node_map[n]["lat"], node_map[n]["lon"]] for n in path_nodes if "lat" in node_map[n]]
        dist = cost_so_far[goal_node]
        
        return {"path": coords, "distance_m": round(dist, 1)}

    def deliberate(self, graph_json: dict, db_session) -> dict:
        """
        Rank hospitals, select best, and compute route (OSRM for vehicle + A* for foot).
        """
        incident_lat = self.beliefs["incident"]["lat"]
        incident_lon = self.beliefs["incident"]["lon"]
        incident_node = self.beliefs["incident"]["node"]
        
        responders = self.beliefs["responders"]
        hospitals = [r for r in responders if r.get("tags", {}).get("amenity") in ("hospital", "clinic")]
        
        # If no OSM hospitals, mock one for demo
        if not hospitals:
            hospitals = [{
                "id": 999999,
                "lat": incident_lat + 0.02,
                "lon": incident_lon - 0.02,
                "tags": {"name": "General Hospital (Synthetic)"}
            }]
            
        ranked_hospitals = []
        
        from app.models import Hospital
        
        for h in hospitals:
            h_id = str(h["id"])
            h_lat = h.get("lat") or h.get("center", {}).get("lat")
            h_lon = h.get("lon") or h.get("center", {}).get("lon")
            h_name = h.get("tags", {}).get("name", "Unknown Hospital")
            
            if not h_lat or not h_lon:
                continue
                
            # Fetch load from DB
            db_hosp = db_session.query(Hospital).filter(Hospital.osm_id == h_id).first()
            if not db_hosp:
                # Create placeholder
                db_hosp = Hospital(osm_id=h_id, name=h_name, lat=h_lat, lon=h_lon, total_beds=100, current_occupancy=60)
                db_session.add(db_hosp)
                db_session.commit()
                db_session.refresh(db_hosp)
                
            dist_m = haversine(h_lat, h_lon, incident_lat, incident_lon)
            # Estimate travel time: 40 km/h avg in city = ~11 m/s -> time = dist / 11
            travel_time_s = dist_m / 11.0 
            
            occupancy_rate = db_hosp.current_occupancy / db_hosp.total_beds if db_hosp.total_beds > 0 else 1.0
            
            # Utility function: lower distance and lower occupancy is better
            # Normalize distance (max ~5000m) and occupancy (0-1)
            dist_norm = min(dist_m / 5000.0, 1.0)
            utility = 100 - (dist_norm * 50) - (occupancy_rate * 50)
            
            ranked_hospitals.append({
                "osm_id": h_id,
                "name": h_name,
                "dist_m": round(dist_m, 1),
                "travel_time_min": round(travel_time_s / 60, 1),
                "occupancy_rate": round(occupancy_rate * 100, 1),
                "utility": round(utility, 2),
                "lat": h_lat,
                "lon": h_lon
            })
            
        ranked_hospitals.sort(key=lambda x: x["utility"], reverse=True)
        
        if not ranked_hospitals:
            return {"error": "No hospitals found"}
            
        best_hosp = ranked_hospitals[0]
        
        # Vehicle routing to twin edge.
        # Find nearest road node in twin graph to the incident
        road_nodes, node_map, _ = self._get_road_and_foot_nodes(graph_json)
        
        nearest_road_node = None
        min_r_dist = float('inf')
        for rn in road_nodes:
            if rn in node_map and "lat" in node_map[rn]:
                d = haversine(node_map[rn]["lat"], node_map[rn]["lon"], incident_lat, incident_lon)
                if d < min_r_dist:
                    min_r_dist = d
                    nearest_road_node = rn
                    
        if not nearest_road_node:
            nearest_road_node = incident_node # Fallback
            
        # OSRM route for vehicle leg
        vehicle_path = []
        try:
            rn_lat, rn_lon = node_map[nearest_road_node]["lat"], node_map[nearest_road_node]["lon"]
            osrm_url = f"http://router.project-osrm.org/route/v1/driving/{best_hosp['lon']},{best_hosp['lat']};{rn_lon},{rn_lat}?overview=full&geometries=geojson"
            r = requests.get(osrm_url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get("routes"):
                    # GeoJSON is lon, lat. We need lat, lon for Leaflet.
                    coords = data["routes"][0]["geometry"]["coordinates"]
                    vehicle_path = [[lat, lon] for lon, lat in coords]
        except Exception as e:
            logger.warning(f"OSRM routing failed: {e}")
            # Fallback direct line
            vehicle_path = [[best_hosp["lat"], best_hosp["lon"]], [node_map[nearest_road_node]["lat"], node_map[nearest_road_node]["lon"]]]

        # Footpath routing inside twin (Road Node -> Incident Node)
        foot_res = self.astar_responder(graph_json, nearest_road_node, incident_node)
        foot_path = foot_res["path"]
        
        return {
            "responder_type": "Ambulance",
            "best_hospital": best_hosp,
            "ranked_hospitals": ranked_hospitals,
            "vehicle_route": vehicle_path,
            "foot_route": foot_path,
            "eta_min": best_hosp["travel_time_min"] + round(foot_res["distance_m"] / 80.0, 1) # 80m/min walking
        }

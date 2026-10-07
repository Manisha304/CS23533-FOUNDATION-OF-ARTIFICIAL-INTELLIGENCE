import networkx as nx
from typing import Dict, List, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def analyze_risk_points(graph_json: dict, gates: List[dict], capacity_estimate: dict = None) -> List[dict]:
    """
    Computes a risk score for each node in the twin graph based on structural and geometric factors.
    Returns a list of dicts with score, reason, lat, lon.
    """
    nodes_raw = graph_json.get("nodes", [])
    links_raw = graph_json.get("links", [])
    
    if not nodes_raw:
        return []

    # 1. Build NetworkX graph
    G = nx.Graph()
    node_map = {}
    for n in nodes_raw:
        nid = str(n["id"])
        node_map[nid] = n
        G.add_node(nid, **n)
        
    for link in links_raw:
        u, v = str(link["source"]), str(link["target"])
        if u in node_map and v in node_map:
            G.add_edge(u, v, **link)
            
    # 2. Structural metrics
    articulation_points = set()
    if len(G) > 0:
        try:
            articulation_points = set(nx.articulation_points(G))
        except Exception as e:
            logger.warning(f"Failed to compute articulation points: {e}")

    centrality = {}
    if len(G) > 0:
        try:
            # We use length as weight for shortest path betweenness if available, or just unweighted.
            centrality = nx.betweenness_centrality(G, weight="length", normalized=True)
        except Exception as e:
            logger.warning(f"Failed to compute betweenness centrality: {e}")
            
    # Determine top N% centrality threshold
    centrality_threshold = 0
    if centrality:
        vals = sorted(centrality.values(), reverse=True)
        idx = int(len(vals) * settings.CENTRALITY_TOP_PERCENT)
        if idx < len(vals):
            centrality_threshold = vals[idx]

    # 3. Overloaded entrance expectations
    gate_expected_arrival = {}
    if capacity_estimate and capacity_estimate.get("estimated_capacity"):
        # Very rough heuristic: if total capacity must exit through G gates within 30 mins
        # we check if required flow > exit throughput.
        cap = capacity_estimate["estimated_capacity"]
        num_gates = len([g for g in gates if g.get("status") != "blocked"]) or 1
        avg_flow = cap / num_gates
        # Just flag gates if average flow per gate is high. (Simplified for E1)
        # We'll use a threshold of 1000 people per gate as a simple metric if no temporal data.
        for g in gates:
            gate_expected_arrival[str(g["id"])] = avg_flow

    # 4. Score nodes
    risk_results = []
    
    for nid, data in node_map.items():
        score = 0
        reasons = []
        
        # Check node/edge tags for stairs/narrowness
        is_stairs = False
        min_width = 999.0
        
        # We check the node itself and its incident edges
        edges = G.edges(nid, data=True)
        for u, v, edata in edges:
            tags = edata.get("tags", {})
            hw = tags.get("highway")
            
            if hw == "steps":
                is_stairs = True
                
            width_source = "estimated (default)"
            width_str = tags.get("width")
            w = None
            if width_str:
                try:
                    w = float(width_str.replace("m", "").strip())
                    width_source = "OSM-tagged"
                except:
                    pass
                    
            if w is None and hw in ["footway", "path", "pedestrian", "steps"]:
                # Try to measure width using satellite imagery
                from app.capacity.path_width import measure_path_width
                # use node data for lat, lon
                n_data = node_map.get(u)
                if n_data and "lat" in n_data and "lon" in n_data:
                    measured = measure_path_width(n_data["lat"], n_data["lon"])
                    if measured > 0:
                        w = measured
                        width_source = "measured from satellite imagery"
                        logger.info(f"Measured path width {w}m at {n_data['lat']}, {n_data['lon']}")
                    else:
                        logger.warning(f"Failed to measure path width at {n_data['lat']}, {n_data['lon']}, falling back to default")
            
            if w is None and hw in settings.DEFAULT_HIGHWAY_WIDTHS:
                w = settings.DEFAULT_HIGHWAY_WIDTHS[hw]
                width_source = "estimated (default)"
                
            if w is not None and w < min_width:
                min_width = w
                node_min_width_source = width_source
                
        # Initialize variable in case it wasn't set (e.g. no incident edges)
        node_min_width_source = locals().get("node_min_width_source", "estimated (default)")
        if is_stairs:
            score += settings.RISK_STAIRS_WEIGHT
            reasons.append("Stairs/steep path")
            
        if min_width < settings.NARROW_WIDTH_THRESHOLD:
            score += settings.RISK_NARROW_WEIGHT
            reasons.append(f"Narrow path (min width {min_width}m, {node_min_width_source})")
            
        if nid in articulation_points:
            score += settings.RISK_ARTICULATION_WEIGHT
            reasons.append("Articulation point (structural bottleneck)")
            
        if centrality.get(nid, 0) >= centrality_threshold and centrality_threshold > 0:
            score += settings.RISK_CENTRALITY_WEIGHT
            reasons.append(f"High traffic node (top {int(settings.CENTRALITY_TOP_PERCENT*100)}% centrality)")
            
        # Throughput check for gates
        if nid in gate_expected_arrival:
            # If expected flow is very high, flag it
            if gate_expected_arrival[nid] > 500: # Arbitrary threshold for demo
                score += settings.RISK_THROUGHPUT_WEIGHT
                reasons.append(f"Overloaded entrance (expected {int(gate_expected_arrival[nid])} agents)")

        score = min(score, 100) # Cap at 100
        
        if score > 0:
            reason_str = ", ".join(reasons)
            risk_results.append({
                "id": nid,
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "score": score,
                "reason": reason_str
            })
            
    return risk_results

"""
Phase 5 — BDI Multi-Agent System for Crowd Management

Agents:
  CrowdAgent     — tracks how many people are at each gate (Belief)
  RouteAgent     — runs A* to compute best exit path (Plan)
  SafetyAgent    — marks gates as blocked (Belief update)
  Coordinator    — utility-based decision: picks best open gate for a crowd zone

All decision logic is classical (no ML). Fully traceable for viva.
"""

import math
import heapq
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# BDI Agent base
# ---------------------------------------------------------------------------

class BDIAgent:
    """Minimal BDI scaffold: Beliefs (dict), Desires (goals), Intentions (plans)."""
    def __init__(self, name: str):
        self.name = name
        self.beliefs: Dict = {}
        self.desires: List[str] = []
        self.intentions: List[str] = []

    def update_belief(self, key: str, value):
        self.beliefs[key] = value
        logger.debug(f"[{self.name}] Belief updated: {key} = {value}")

    def deliberate(self) -> List[str]:
        """Override in subclasses to compute intentions from beliefs+desires."""
        return []


# ---------------------------------------------------------------------------
# SafetyAgent — manages which gates are open / blocked
# ---------------------------------------------------------------------------

class SafetyAgent(BDIAgent):
    """
    Belief:  gate_status  {gate_id: 'open' | 'blocked'}
    Desire:  keep all exits accessible
    Intention: flag blocked gates so RouteAgent avoids them
    """
    def __init__(self, gates: List[dict]):
        super().__init__("SafetyAgent")
        self.beliefs["gate_status"] = {g["id"]: "open" for g in gates}
        self.desires = ["maximize_open_exits"]

    def block_gate(self, gate_id: str, reason: str = "manual"):
        self.beliefs["gate_status"][gate_id] = "blocked"
        logger.info(f"[SafetyAgent] Gate {gate_id} BLOCKED. Reason: {reason}")

    def open_gate(self, gate_id: str):
        self.beliefs["gate_status"][gate_id] = "open"
        logger.info(f"[SafetyAgent] Gate {gate_id} OPENED.")

    def open_gates(self) -> List[str]:
        return [gid for gid, status in self.beliefs["gate_status"].items() if status == "open"]

    def deliberate(self) -> List[str]:
        blocked = [g for g, s in self.beliefs["gate_status"].items() if s == "blocked"]
        if blocked:
            self.intentions = [f"reroute_from_{g}" for g in blocked]
        else:
            self.intentions = ["monitor"]
        return self.intentions


# ---------------------------------------------------------------------------
# CrowdAgent — tracks crowd at each gate
# ---------------------------------------------------------------------------

class CrowdAgent(BDIAgent):
    """
    Belief:  crowd_count {gate_id: int}
    Desire:  crowd_count at each gate ≤ capacity_per_gate
    Intention: signal congestion if over threshold
    """
    def __init__(self, gates: List[dict], capacity_per_gate: int = 1000):
        super().__init__("CrowdAgent")
        self.beliefs["crowd_count"] = {g["id"]: 0 for g in gates}
        self.beliefs["capacity_per_gate"] = capacity_per_gate
        self.desires = ["balance_crowd_across_gates"]

    def update_crowd(self, gate_id: str, count: int):
        self.beliefs["crowd_count"][gate_id] = count

    def congested_gates(self) -> List[str]:
        cap = self.beliefs["capacity_per_gate"]
        return [g for g, c in self.beliefs["crowd_count"].items() if c >= cap]

    def deliberate(self) -> List[str]:
        congested = self.congested_gates()
        if congested:
            self.intentions = [f"redistribute_from_{g}" for g in congested]
        else:
            self.intentions = ["maintain_flow"]
        return self.intentions


# ---------------------------------------------------------------------------
# RouteAgent — A* rerouting
# ---------------------------------------------------------------------------

class RouteAgent(BDIAgent):
    """
    Belief:  graph nodes + edges, blocked_gates set
    Desire:  find shortest path to an open, uncongested gate
    Intention: execute A* and return waypoints
    """
    def __init__(self):
        super().__init__("RouteAgent")
        self.beliefs["graph"] = None  # set externally

    def set_graph(self, graph_json: dict):
        self.beliefs["graph"] = graph_json

    def astar(
        self,
        graph_json: dict,
        start_lat: float,
        start_lon: float,
        goal_gate_ids: List[str],
        blocked_nodes: set = None,
        risk_scores: dict = None,
    ) -> dict:
        """
        A* from (start_lat, start_lon) to the nearest open gate.

        Returns:
          {
            "path": [[lat, lon], ...],
            "gate_id": str,
            "distance_m": float,
            "algorithm": "A*",
            "heuristic": "Haversine",
          }
        """
        if blocked_nodes is None:
            blocked_nodes = set()

        nodes_raw = graph_json.get("nodes", [])
        links_raw = graph_json.get("links", [])

        # Build adjacency map
        node_map: Dict[str, dict] = {}
        for n in nodes_raw:
            node_map[str(n["id"])] = n

        adj: Dict[str, List[Tuple[str, float]]] = {nid: [] for nid in node_map}
        for link in links_raw:
            u, v = str(link["source"]), str(link["target"])
            w = link.get("length", 1.0)
            if u in adj and v in adj:
                adj[u].append((v, w))
                adj[v].append((u, w))

        # Find the graph node nearest to start_lat/start_lon
        start_node = min(
            node_map,
            key=lambda nid: haversine(start_lat, start_lon, node_map[nid]["lat"], node_map[nid]["lon"])
            if "lat" in node_map[nid] else float("inf"),
            default=None,
        )
        if not start_node:
            return {"error": "Graph is empty"}

        best_result = None
        best_cost = float("inf")

        for goal_id in goal_gate_ids:
            if goal_id not in node_map:
                continue
            goal_node = node_map[goal_id]

            # A* search
            pq = [(0.0, start_node)]
            came_from: Dict[str, Optional[str]] = {start_node: None}
            cost_so_far: Dict[str, float] = {start_node: 0.0}

            found = False
            while pq:
                current_f, current = heapq.heappop(pq)

                if current == goal_id:
                    found = True
                    break

                for neighbor, w in adj.get(current, []):
                    if neighbor in blocked_nodes:
                        continue
                        
                    # Apply risk penalty if any
                    penalty = 0.0
                    if risk_scores and neighbor in risk_scores:
                        from app.config import settings
                        penalty = risk_scores[neighbor] * settings.RISK_ROUTE_PENALTY_MULTIPLIER
                        
                    new_cost = cost_so_far[current] + w + penalty
                    
                    if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                        cost_so_far[neighbor] = new_cost
                        nb = node_map[neighbor]
                        h = haversine(nb["lat"], nb["lon"], goal_node["lat"], goal_node["lon"]) if "lat" in nb else 0
                        heapq.heappush(pq, (new_cost + h, neighbor))
                        came_from[neighbor] = current

            if found and cost_so_far.get(goal_id, float("inf")) < best_cost:
                best_cost = cost_so_far[goal_id]
                # Reconstruct path
                path_nodes = []
                cur = goal_id
                while cur is not None:
                    path_nodes.append(cur)
                    cur = came_from.get(cur)
                path_nodes.reverse()
                best_result = {
                    "path": [[node_map[n]["lat"], node_map[n]["lon"]] for n in path_nodes if "lat" in node_map[n]],
                    "path_node_ids": path_nodes,
                    "gate_id": goal_id,
                    "distance_m": round(best_cost, 1),
                    "algorithm": "A*",
                    "heuristic": "Haversine",
                    "node_count": len(path_nodes),
                }

        if not best_result:
            return {"error": "No reachable open gate found", "path": []}

        logger.info(f"[RouteAgent] Best route: gate={best_result['gate_id']}, dist={best_result['distance_m']}m")
        return best_result


# ---------------------------------------------------------------------------
# Coordinator — utility-based gate selection
# ---------------------------------------------------------------------------

class Coordinator:
    """
    Utility-based agent: scores each open gate and picks the best one.
    Utility = (1/distance) * (1 - crowd_load)
    where crowd_load = crowd_count / capacity_per_gate  (0..1)
    Fully explainable: each factor is printed.
    """
    def __init__(self, safety_agent: SafetyAgent, crowd_agent: CrowdAgent, route_agent: RouteAgent):
        self.safety = safety_agent
        self.crowd = crowd_agent
        self.route = route_agent

    def best_gate(
        self,
        graph_json: dict,
        zone_lat: float,
        zone_lon: float,
        gates: List[dict],
        risk_scores: dict = None,
    ) -> dict:
        open_gate_ids = self.safety.open_gates()
        cap = self.crowd.beliefs["capacity_per_gate"]

        # Score each open gate
        scores = []
        for gate in gates:
            gid = gate["id"]
            if gid not in open_gate_ids:
                continue
            dist = haversine(zone_lat, zone_lon, gate["lat"], gate["lon"])
            crowd = self.crowd.beliefs["crowd_count"].get(gid, 0)
            load = min(crowd / cap, 1.0) if cap > 0 else 0.0
            utility = (1.0 / (dist + 1)) * (1.0 - load)
            scores.append((utility, gid, dist, load))

        if not scores:
            return {"error": "All gates are blocked or unavailable"}

        scores.sort(reverse=True)
        best_utility, best_gid, best_dist, best_load = scores[0]

        # Route to that gate
        route = self.route.astar(graph_json, zone_lat, zone_lon, [best_gid], risk_scores=risk_scores)

        reasoning = f"Gate {best_gid} selected: utility={best_utility:.4f}, dist={best_dist:.0f}m, load={best_load*100:.0f}%"
        
        # Risk reasoning
        if risk_scores and route.get("path_node_ids"):
            path_nodes = route["path_node_ids"]
            path_risks = [risk_scores.get(n, 0) for n in path_nodes]
            max_risk = max(path_risks) if path_risks else 0
            if max_risk > 50:
                reasoning += f" [Route] Using path with high-risk bottleneck (score {max_risk})."
            elif max_risk > 0:
                reasoning += f" [Route] Avoiding high-risk bottlenecks (max score encountered {max_risk})."
            else:
                reasoning += f" [Route] Clean path, avoiding all high-risk bottlenecks."

        return {
            "selected_gate": best_gid,
            "utility": round(best_utility, 4),
            "distance_m": round(best_dist, 1),
            "crowd_load_pct": round(best_load * 100, 1),
            "reasoning": reasoning,
            "route": route,
            "all_scores": [{"gate": s[1], "utility": round(s[0], 4), "dist_m": round(s[2], 1), "load_pct": round(s[3]*100,1)} for s in scores],
        }

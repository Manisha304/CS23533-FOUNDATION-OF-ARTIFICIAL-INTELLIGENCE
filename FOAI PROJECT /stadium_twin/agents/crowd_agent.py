"""
stadium_twin/agents/crowd_agent.py
==================================
Crowd Agent Module.

Role in Multi-Agent Architecture:
- Sensing & Monitoring Agent.
- Evaluates real-time occupancy loads against capacity thresholds.
- Detects bottlenecks, warning zones, and critical overloads.

Classical AI Concepts:
- Rule-based State Classification.
- Priority Ranking by Severity (Sorting by load factor).
"""

from typing import Dict, Any, List, Tuple

# --- Threshold Constants (No Magic Numbers) ---
WARNING_THRESHOLD = 0.70    # 70% capacity triggers yellow warning
OVERLOAD_THRESHOLD = 0.90   # 90% capacity triggers red overload alert

STATUS_OK = "OK"
STATUS_WARNING = "WARNING"
STATUS_OVERLOADED = "OVERLOADED"
STATUS_BLOCKED = "BLOCKED"


class CrowdAgent:
    """
    Monitors stadium graph occupancy and classifies nodes based on crowd density.
    """

    def __init__(self, warning_thresh: float = WARNING_THRESHOLD, overload_thresh: float = OVERLOAD_THRESHOLD):
        """
        Initialize CrowdAgent with configurable occupancy thresholds.
        
        Args:
            warning_thresh: Occupancy ratio above which node is classified as WARNING.
            overload_thresh: Occupancy ratio above which node is classified as OVERLOADED.
        """
        self.warning_threshold = warning_thresh
        self.overload_threshold = overload_thresh

    def analyze(self, graph_state: Dict[str, Any]) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
        """
        Analyze current stadium graph state.
        
        Args:
            graph_state: Snapshot dict from StadiumGraph.get_state()
            
        Returns:
            Tuple containing:
            1. node_statuses: dict of node_id -> status string ("OK", "WARNING", "OVERLOADED", "BLOCKED")
            2. overloaded_nodes: list of dicts for overloaded nodes sorted descending by severity/load_factor.
        """
        node_statuses: Dict[str, str] = {}
        overloaded_nodes: List[Dict[str, Any]] = []

        nodes = graph_state.get("nodes", {})

        for node_id, data in nodes.items():
            is_blocked = data.get("blocked", False)
            load_factor = data.get("load_factor", 0.0)
            capacity = data.get("capacity", 1)
            current_load = data.get("current_load", 0)

            if is_blocked:
                status = STATUS_BLOCKED
            elif load_factor >= self.overload_threshold:
                status = STATUS_OVERLOADED
                overloaded_nodes.append({
                    "node": node_id,
                    "load_factor": load_factor,
                    "current_load": current_load,
                    "capacity": capacity,
                    "excess_people": max(0, current_load - int(capacity * self.overload_threshold))
                })
            elif load_factor >= self.warning_threshold:
                status = STATUS_WARNING
            else:
                status = STATUS_OK

            node_statuses[node_id] = status

        # Sort overloaded nodes descending by severity (highest load factor first)
        overloaded_nodes.sort(key=lambda item: item["load_factor"], reverse=True)

        return node_statuses, overloaded_nodes


if __name__ == "__main__":
    from stadium_twin.graph_model import StadiumGraph
    sg = StadiumGraph()
    sg.set_load("Gate_A", 4800)  # 96% -> Overloaded
    sg.set_load("Gate_B", 3800)  # 76% -> Warning
    sg.block_node("Gate_D")
    
    agent = CrowdAgent()
    statuses, overloaded = agent.analyze(sg.get_state())
    print("Node Statuses:", statuses)
    print("Overloaded Nodes (Sorted):", overloaded)

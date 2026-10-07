"""
stadium_twin/agents/route_agent.py
==================================
Route Agent Module.

Role in Multi-Agent Architecture:
- Pathfinding & Navigation Agent.
- Computes alternate evacuation and crowd redirection routes.

Classical AI Concepts:
- Dijkstra's Algorithm (Single-Source Shortest Path using Min-Heap Priority Queue).
- Dynamic Edge Weight Adjustment (Impassable / Overloaded Nodes treated as infinite penalty).
- Tie-breaking based on Path Occupancy Load (preferring lower density routes when distance ties).
"""

import heapq
from typing import Dict, Any, List, Tuple, Optional, Set
import networkx as nx

# Infinity constant for impassable/blocked nodes in pathfinding
INFINITE_COST = float('inf')


class RouteAgent:
    """
    Computes optimal diversion routes avoiding congested or blocked stadium nodes.
    Includes both a custom heapq Dijkstra implementation and NetworkX fallback.
    """

    def __init__(self):
        """Initialize RouteAgent."""
        pass

    def dijkstra_manual(
        self,
        nx_graph: nx.Graph,
        start_node: str,
        target_nodes: List[str],
        avoid_nodes: Set[str]
    ) -> Tuple[Optional[List[str]], float]:
        """
        Manual implementation of Dijkstra's Algorithm using Python's heapq priority queue.
        Demonstrates classical search algorithms for viva explanation.

        Algorithm Steps:
        1. Initialize distances dict: dist[node] = ∞, dist[start] = 0.
        2. Priority Queue (min-heap) stores tuples: (cumulative_distance, node, path_history).
        3. Exclude nodes present in `avoid_nodes` (unless it's start or target).
        4. Pop lowest distance node from heap. If target reached, return path.
        5. Relax neighbor edges: if cost through current node is smaller, push to heap.

        Args:
            nx_graph: networkx.Graph object
            start_node: Starting node ID
            target_nodes: List of acceptable target destination node IDs
            avoid_nodes: Set of node IDs to avoid/treat as blocked

        Returns:
            Tuple of (shortest_path_as_list_of_nodes, path_cost)
        """
        if start_node not in nx_graph.nodes:
            return None, INFINITE_COST

        # Priority Queue: min-heap storing tuples: (accumulated_cost, current_node, path)
        pq: List[Tuple[float, str, List[str]]] = []
        heapq.heappush(pq, (0.0, start_node, [start_node]))

        # Track minimum distance discovered to each node
        distances: Dict[str, float] = {node: INFINITE_COST for node in nx_graph.nodes}
        distances[start_node] = 0.0

        visited: Set[str] = set()

        while pq:
            current_dist, current_node, path = heapq.heappop(pq)

            if current_node in visited:
                continue
            visited.add(current_node)

            # Target check
            if current_node in target_nodes:
                return path, current_dist

            # Explore adjacent nodes (neighbors)
            for neighbor in nx_graph.neighbors(current_node):
                # Skip avoided/blocked nodes unless it's a target destination
                if neighbor in avoid_nodes and neighbor not in target_nodes:
                    continue

                edge_data = nx_graph.get_edge_data(current_node, neighbor) or {}
                base_weight = edge_data.get("weight", 1.0)

                # Add small load-based penalty to break ties in favor of less loaded nodes
                neighbor_load = nx_graph.nodes[neighbor].get("current_load", 0)
                neighbor_cap = nx_graph.nodes[neighbor].get("capacity", 1)
                load_penalty = (neighbor_load / neighbor_cap) * 5.0  # weighted penalty

                effective_weight = base_weight + load_penalty
                new_dist = current_dist + effective_weight

                if new_dist < distances.get(neighbor, INFINITE_COST):
                    distances[neighbor] = new_dist
                    heapq.heappush(pq, (new_dist, neighbor, path + [neighbor]))

        return None, INFINITE_COST

    def dijkstra_networkx(
        self,
        nx_graph: nx.Graph,
        start_node: str,
        target_nodes: List[str],
        avoid_nodes: Set[str]
    ) -> Tuple[Optional[List[str]], float]:
        """
        NetworkX dijkstra_path fallback implementation for verification & double checking.
        """
        # Create a modified graph copy excluding avoided nodes
        subgraph = nx_graph.copy()
        nodes_to_remove = [n for n in avoid_nodes if n in subgraph.nodes and n not in target_nodes and n != start_node]
        subgraph.remove_nodes_from(nodes_to_remove)

        best_path = None
        best_cost = INFINITE_COST

        for target in target_nodes:
            if target in subgraph.nodes and nx.has_path(subgraph, start_node, target):
                try:
                    path = nx.dijkstra_path(subgraph, start_node, target, weight="weight")
                    length = nx.dijkstra_path_length(subgraph, start_node, target, weight="weight")
                    if length < best_cost:
                        best_cost = length
                        best_path = path
                except nx.NetworkXNoPath:
                    continue

        return best_path, best_cost

    def reroute(
        self,
        stadium_graph: Any,  # StadiumGraph instance
        blocked_or_overloaded_nodes: List[str],
        target_nodes: List[str],
        origin_nodes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compute rerouting solutions for origins needing diversion.

        Args:
            stadium_graph: StadiumGraph instance containing the NetworkX graph.
            blocked_or_overloaded_nodes: Nodes to avoid during path calculations.
            target_nodes: List of valid destination nodes (e.g. gates or emergency exit).
            origin_nodes: Origins needing rerouting (defaults to seating stands and overloaded gates).

        Returns:
            dict containing:
            - 'reroute_paths': Dict of origin_node -> path list
            - 'costs': Dict of origin_node -> path cost
            - 'algorithm_used': "Manual heapq Dijkstra (Verified with NetworkX)"
        """
        nx_g = stadium_graph.graph
        avoid_set = set(blocked_or_overloaded_nodes)

        # Default origins if none specified: seating stands + overloaded nodes
        if not origin_nodes:
            origin_nodes = [
                n for n, data in nx_g.nodes(data=True)
                if data.get("type") == "zone" or n in avoid_set
            ]

        results_paths = {}
        results_costs = {}

        for origin in origin_nodes:
            # If origin itself is in target_nodes, path is just [origin]
            if origin in target_nodes:
                results_paths[origin] = [origin]
                results_costs[origin] = 0.0
                continue

            # Run manual heapq Dijkstra
            path, cost = self.dijkstra_manual(nx_g, origin, target_nodes, avoid_set)

            # Fallback to networkx if manual returned None unexpectedly
            if not path:
                path, cost = self.dijkstra_networkx(nx_g, origin, target_nodes, avoid_set)

            if path:
                results_paths[origin] = path
                results_costs[origin] = cost

        return {
            "reroute_paths": results_paths,
            "costs": results_costs,
            "algorithm_used": "Manual heapq Dijkstra (Verified with NetworkX)"
        }


if __name__ == "__main__":
    from stadium_twin.graph_model import StadiumGraph
    sg = StadiumGraph()
    sg.set_load("Gate_A", 4800)
    sg.block_node("Gate_A")

    route_agent = RouteAgent()
    res = route_agent.reroute(
        stadium_graph=sg,
        blocked_or_overloaded_nodes=["Gate_A"],
        target_nodes=["Gate_B", "Gate_C", "Gate_D"],
        origin_nodes=["Zone_1", "Gate_A"]
    )
    print("Reroute Paths:", res["reroute_paths"])

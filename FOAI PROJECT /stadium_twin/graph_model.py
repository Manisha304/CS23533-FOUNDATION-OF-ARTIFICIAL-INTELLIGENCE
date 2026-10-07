"""
stadium_twin/graph_model.py
===========================
Stadium Digital Twin Graph Representation.

This module encapsulates a stadium topological layout using NetworkX (networkx.Graph).
Nodes represent spatial zones (Gates, Seating Stands, Junctions, Concourses, Emergency Exits).
Edges represent pedestrian walkways with physical distances (weights).

Classical AI / Data Structure Concept:
- Graph G = (V, E) where V are vertices (stadium locations) and E are weighted edges (walkways).
- Adjacency list representation provided natively by NetworkX.
"""

from typing import Dict, Any, List, Optional
import networkx as nx

# --- Named Constants for Capacity & Types (No Magic Numbers) ---
DEFAULT_GATE_CAPACITY = 5000       # Max people per entry/exit gate
DEFAULT_ZONE_CAPACITY = 8000       # Max seating capacity per stand/zone
DEFAULT_JUNCTION_CAPACITY = 4000   # Max bottleneck capacity for concourse junctions
DEFAULT_PARKING_CAPACITY = 12000   # Max parking area capacity
DEFAULT_EXIT_CAPACITY = 15000      # Max emergency exit throughput capacity

# Spatial Node Types
TYPE_GATE = "gate"
TYPE_ZONE = "zone"
TYPE_JUNCTION = "junction"
TYPE_PARKING = "parking"
TYPE_EXIT = "exit"


class StadiumGraph:
    """
    Wraps a NetworkX Graph to represent stadium layout, spatial attributes,
    crowd load tracking, and structural blockages.
    """

    def __init__(self):
        """Initialize an empty NetworkX graph and default state structures."""
        self.graph = nx.Graph()
        self.load_default_layout()

    def load_default_layout(self) -> None:
        """
        Builds the default 13-node stadium topology.
        
        Spatial Layout Schema:
        - 4 Entry/Exit Gates: Gate_A, Gate_B, Gate_C, Gate_D
        - 3 Seating Stands: Zone_1 (North), Zone_2 (East), Zone_3 (South)
        - 2 Pathway Junctions: Junction_1 (West), Junction_2 (East)
        - 2 Concourses: Concourse_North, Concourse_South
        - 1 Facility: Parking_Area
        - 1 Dedicated Emergency Exit: Emergency_Exit
        """
        self.graph.clear()

        # Define 13 Stadium Nodes with Spatial Attributes and Layout Coordinates (x, y)
        nodes_data = [
            # Entry Gates (Outer Perimeter)
            ("Gate_A", {"type": TYPE_GATE, "capacity": DEFAULT_GATE_CAPACITY, "pos": (-2.0, 2.0)}),
            ("Gate_B", {"type": TYPE_GATE, "capacity": DEFAULT_GATE_CAPACITY, "pos": (2.0, 2.0)}),
            ("Gate_C", {"type": TYPE_GATE, "capacity": DEFAULT_GATE_CAPACITY, "pos": (2.0, -2.0)}),
            ("Gate_D", {"type": TYPE_GATE, "capacity": DEFAULT_GATE_CAPACITY, "pos": (-2.0, -2.0)}),

            # Concourses & Pathway Junctions (Intermediate Ring)
            ("Concourse_North", {"type": TYPE_JUNCTION, "capacity": DEFAULT_JUNCTION_CAPACITY, "pos": (0.0, 2.0)}),
            ("Concourse_South", {"type": TYPE_JUNCTION, "capacity": DEFAULT_JUNCTION_CAPACITY, "pos": (0.0, -2.0)}),
            ("Junction_1", {"type": TYPE_JUNCTION, "capacity": DEFAULT_JUNCTION_CAPACITY, "pos": (-1.0, 0.0)}),
            ("Junction_2", {"type": TYPE_JUNCTION, "capacity": DEFAULT_JUNCTION_CAPACITY, "pos": (1.0, 0.0)}),

            # Seating Stands (Inner Core)
            ("Zone_1", {"type": TYPE_ZONE, "capacity": DEFAULT_ZONE_CAPACITY, "pos": (-0.8, 1.0)}),
            ("Zone_2", {"type": TYPE_ZONE, "capacity": DEFAULT_ZONE_CAPACITY, "pos": (0.8, 1.0)}),
            ("Zone_3", {"type": TYPE_ZONE, "capacity": DEFAULT_ZONE_CAPACITY, "pos": (0.0, -1.0)}),

            # External Facilities & Safety Exits
            ("Parking_Area", {"type": TYPE_PARKING, "capacity": DEFAULT_PARKING_CAPACITY, "pos": (-3.0, 0.0)}),
            ("Emergency_Exit", {"type": TYPE_EXIT, "capacity": DEFAULT_EXIT_CAPACITY, "pos": (0.0, 3.2)})
        ]

        # Add Nodes with default initial state (current_load = 0, blocked = False)
        for node_id, attrs in nodes_data:
            self.graph.add_node(
                node_id,
                type=attrs["type"],
                capacity=attrs["capacity"],
                current_load=0,
                blocked=False,
                pos=attrs["pos"]
            )

        # Define Edges with Walking Distance Weights (in meters / travel cost)
        edges_data = [
            # Gate Connections to Concourses / Junctions / Parking
            ("Gate_A", "Parking_Area", 50),
            ("Gate_A", "Concourse_North", 40),
            ("Gate_A", "Junction_1", 45),
            
            ("Gate_B", "Concourse_North", 40),
            ("Gate_B", "Junction_2", 45),
            ("Gate_B", "Emergency_Exit", 60),

            ("Gate_C", "Concourse_South", 40),
            ("Gate_C", "Junction_2", 45),

            ("Gate_D", "Parking_Area", 50),
            ("Gate_D", "Concourse_South", 40),
            ("Gate_D", "Junction_1", 45),

            # Concourse & Junction Core Connections
            ("Concourse_North", "Zone_1", 25),
            ("Concourse_North", "Zone_2", 25),
            ("Concourse_North", "Emergency_Exit", 30),

            ("Concourse_South", "Zone_3", 25),
            ("Concourse_South", "Junction_1", 35),
            ("Concourse_South", "Junction_2", 35),

            ("Junction_1", "Zone_1", 20),
            ("Junction_1", "Zone_3", 30),
            ("Junction_1", "Concourse_North", 35),

            ("Junction_2", "Zone_2", 20),
            ("Junction_2", "Zone_3", 30),
            ("Junction_2", "Concourse_North", 35),

            # Inter-stand Walkways
            ("Zone_1", "Zone_2", 40),
            ("Zone_1", "Emergency_Exit", 50)
        ]

        for u, v, weight in edges_data:
            self.graph.add_edge(u, v, weight=weight)

    def set_load(self, node: str, count: int) -> None:
        """Update current pedestrian occupancy load for a given node."""
        if node in self.graph.nodes:
            self.graph.nodes[node]["current_load"] = max(0, count)
        else:
            raise KeyError(f"Node '{node}' does not exist in StadiumGraph.")

    def block_node(self, node: str) -> None:
        """Mark a node as structurally blocked (impassable/closed)."""
        if node in self.graph.nodes:
            self.graph.nodes[node]["blocked"] = True
        else:
            raise KeyError(f"Node '{node}' does not exist in StadiumGraph.")

    def unblock_node(self, node: str) -> None:
        """Unblock a previously blocked node."""
        if node in self.graph.nodes:
            self.graph.nodes[node]["blocked"] = False
        else:
            raise KeyError(f"Node '{node}' does not exist in StadiumGraph.")

    def reset_state(self) -> None:
        """Reset all node loads to zero and clear blockages."""
        for node in self.graph.nodes:
            self.graph.nodes[node]["current_load"] = 0
            self.graph.nodes[node]["blocked"] = False

    def get_state(self) -> Dict[str, Any]:
        """
        Returns a complete, immutable dictionary snapshot of graph state.
        
        Returns:
            dict containing:
            - 'nodes': Dict of node_id -> {type, capacity, current_load, load_factor, blocked, pos}
            - 'edges': List of tuples (u, v, weight)
        """
        nodes_snapshot = {}
        for n, data in self.graph.nodes(data=True):
            cap = data.get("capacity", 1)
            load = data.get("current_load", 0)
            load_factor = load / cap if cap > 0 else 0.0
            nodes_snapshot[n] = {
                "type": data.get("type", "unknown"),
                "capacity": cap,
                "current_load": load,
                "load_factor": round(load_factor, 4),
                "blocked": data.get("blocked", False),
                "pos": data.get("pos", (0.0, 0.0))
            }

        edges_snapshot = [
            (u, v, data.get("weight", 1.0))
            for u, v, data in self.graph.edges(data=True)
        ]

        return {
            "nodes": nodes_snapshot,
            "edges": edges_snapshot
        }


# Quick test execution when file is run directly
if __name__ == "__main__":
    sg = StadiumGraph()
    sg.set_load("Gate_A", 4800)
    sg.block_node("Gate_D")
    state = sg.get_state()
    print(f"StadiumGraph loaded with {len(state['nodes'])} nodes and {len(state['edges'])} edges.")
    print(f"Gate_A state: {state['nodes']['Gate_A']}")
    print(f"Gate_D state: {state['nodes']['Gate_D']}")

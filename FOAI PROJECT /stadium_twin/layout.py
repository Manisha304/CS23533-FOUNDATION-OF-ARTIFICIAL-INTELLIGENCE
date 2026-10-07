"""
stadium_twin/layout.py
======================
Chepauk Stadium (MA Chidambaram Stadium, Chennai) Layout Definition.

Maps spatial stadium elements (Stands, Perimeter Gates, Pathways, Parking, Emergency Exit)
to exact (x, y) pixel coordinates on a 1000x800 Pygame canvas.
Maintains a 1-to-1 mapping with an underlying NetworkX topological graph for pathfinding logic.

Classical AI Concept:
- Graph G = (V, E) embedded in 2D Euclidean metric space.
- Spatial Node Coordinates enable seamless crowd sprite motion along graph edges.
"""

from typing import Dict, Any, List, Tuple, Optional
import networkx as nx

# Window Dimensions
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800

# Capacity Constants (No magic numbers)
GATE_CAPACITY = 3000
STAND_CAPACITY = 5000
CONCOURSE_CAPACITY = 4000
PARKING_CAPACITY = 8000
EXIT_CAPACITY = 10000

# Node Types
TYPE_GATE = "gate"
TYPE_STAND = "stand"
TYPE_JUNCTION = "junction"
TYPE_PARKING = "parking"
TYPE_EXIT = "exit"


class ChepaukLayout:
    """
    Defines pixel coordinates, shape dimensions, and NetworkX graph topology
    for MA Chidambaram Stadium (Chepauk), Chennai.
    """

    def __init__(self):
        """Initialize NetworkX graph mapped to 1000x800 canvas coordinates."""
        self.graph = nx.Graph()
        self._build_chepauk_graph()

    def _build_chepauk_graph(self) -> None:
        """Construct graph vertices and weighted edges matching pixel layout."""
        self.graph.clear()

        # 13 Chepauk Nodes with exact (x, y) pixel coordinates
        nodes_data = [
            # 4 Perimeter Gates (Real Chepauk Gate Entrances)
            ("Gate_1_Wallajah",   {"type": TYPE_GATE, "capacity": GATE_CAPACITY, "pos": (500, 70),  "label": "Gate 1 (Wallajah Rd)"}),
            ("Gate_2_Bells",      {"type": TYPE_GATE, "capacity": GATE_CAPACITY, "pos": (910, 360), "label": "Gate 2 (Bells Rd)"}),
            ("Gate_3_Pattabiram", {"type": TYPE_GATE, "capacity": GATE_CAPACITY, "pos": (500, 730), "label": "Gate 3 (Pattabiram Rd)"}),
            ("Gate_4_Vattaram",   {"type": TYPE_GATE, "capacity": GATE_CAPACITY, "pos": (120, 360), "label": "Gate 4 (Vattaram Rd)"}),

            # Walkway Concourses & Junctions
            ("Concourse_North",   {"type": TYPE_JUNCTION, "capacity": CONCOURSE_CAPACITY, "pos": (500, 130), "label": "North Concourse"}),
            ("Concourse_South",   {"type": TYPE_JUNCTION, "capacity": CONCOURSE_CAPACITY, "pos": (500, 650), "label": "South Concourse"}),
            ("Junction_West",     {"type": TYPE_JUNCTION, "capacity": CONCOURSE_CAPACITY, "pos": (200, 360), "label": "West Junction"}),
            ("Junction_East",     {"type": TYPE_JUNCTION, "capacity": CONCOURSE_CAPACITY, "pos": (810, 360), "label": "East Junction"}),

            # 5 Real Chepauk Seating Stands (Curved Seating Bowl)
            ("Anna_Pavilion",        {"type": TYPE_STAND, "capacity": STAND_CAPACITY, "pos": (500, 190), "label": "Anna Pavilion (North)"}),
            ("Pavilion_Stand",       {"type": TYPE_STAND, "capacity": STAND_CAPACITY, "pos": (500, 590), "label": "Pavilion Stand (South)"}),
            ("P4_Upper_Stand",       {"type": TYPE_STAND, "capacity": STAND_CAPACITY, "pos": (720, 360), "label": "P4 Upper Stand (East)"}),
            ("CD_Stand",             {"type": TYPE_STAND, "capacity": STAND_CAPACITY, "pos": (280, 360), "label": "C & D Stand (West)"}),
            ("MA_Chidambaram_Stand", {"type": TYPE_STAND, "capacity": STAND_CAPACITY, "pos": (500, 270), "label": "MA Chidambaram Grandstand"}),

            # External Facilities & Safety Exit
            ("Parking_Area",   {"type": TYPE_PARKING, "capacity": PARKING_CAPACITY, "pos": (80, 680),  "label": "Chepauk Parking Lot"}),
            ("Emergency_Exit", {"type": TYPE_EXIT,    "capacity": EXIT_CAPACITY,    "pos": (860, 80),  "label": "EMERGENCY SAFETY EXIT"})
        ]

        for node_id, attrs in nodes_data:
            self.graph.add_node(
                node_id,
                type=attrs["type"],
                capacity=attrs["capacity"],
                current_load=0,
                blocked=False,
                pos=attrs["pos"],
                label=attrs["label"]
            )

        # Edges with Euclidean distance weights (pixels)
        edges_data = [
            # Gate Connections to Concourses / Junctions / Parking
            ("Gate_1_Wallajah", "Concourse_North", 60),
            ("Gate_1_Wallajah", "Emergency_Exit", 360),
            ("Gate_4_Vattaram", "Parking_Area", 320),
            ("Gate_4_Vattaram", "Junction_West", 80),
            ("Gate_3_Pattabiram", "Concourse_South", 80),
            ("Gate_3_Pattabiram", "Parking_Area", 420),
            ("Gate_2_Bells", "Junction_East", 100),
            ("Gate_2_Bells", "Emergency_Exit", 280),

            # Concourse & Junction Connections to Seating Stands
            ("Concourse_North", "Anna_Pavilion", 60),
            ("Concourse_North", "Junction_West", 370),
            ("Concourse_North", "Junction_East", 370),
            ("Concourse_North", "Emergency_Exit", 360),

            ("Concourse_South", "Pavilion_Stand", 60),
            ("Concourse_South", "Junction_West", 370),
            ("Concourse_South", "Junction_East", 370),

            ("Junction_West", "CD_Stand", 80),
            ("Junction_West", "Concourse_North", 370),
            ("Junction_West", "Concourse_South", 370),

            ("Junction_East", "P4_Upper_Stand", 90),
            ("Junction_East", "Concourse_North", 370),
            ("Junction_East", "Concourse_South", 370),

            # Inner Bowl Connections between Stands
            ("Anna_Pavilion", "MA_Chidambaram_Stand", 80),
            ("MA_Chidambaram_Stand", "CD_Stand", 240),
            ("MA_Chidambaram_Stand", "P4_Upper_Stand", 240),
            ("CD_Stand", "Pavilion_Stand", 280),
            ("P4_Upper_Stand", "Pavilion_Stand", 280),

            # Direct Access to Emergency Exit from North Stand & East Junction
            ("Anna_Pavilion", "Emergency_Exit", 370),
            ("Junction_East", "Emergency_Exit", 280)
        ]

        for u, v, w in edges_data:
            self.graph.add_edge(u, v, weight=w)

    def get_pixel_pos(self, node_id: str) -> Tuple[int, int]:
        """Returns the (x, y) canvas pixel coordinate tuple for a given node."""
        if node_id in self.graph.nodes:
            return self.graph.nodes[node_id]["pos"]
        return (500, 400)  # Default center fallback

    def set_load(self, node: str, count: int) -> None:
        """Set occupancy count for node."""
        if node in self.graph.nodes:
            self.graph.nodes[node]["current_load"] = max(0, count)

    def block_node(self, node: str) -> None:
        """Mark node as blocked."""
        if node in self.graph.nodes:
            self.graph.nodes[node]["blocked"] = True

    def unblock_node(self, node: str) -> None:
        """Unblock node."""
        if node in self.graph.nodes:
            self.graph.nodes[node]["blocked"] = False

    def reset_state(self) -> None:
        """Reset all node loads and blockages."""
        for n in self.graph.nodes:
            self.graph.nodes[n]["current_load"] = 0
            self.graph.nodes[n]["blocked"] = False

    def get_state(self) -> Dict[str, Any]:
        """Returns snapshot dictionary of layout state."""
        nodes_snap = {}
        for n, d in self.graph.nodes(data=True):
            cap = d.get("capacity", 1)
            load = d.get("current_load", 0)
            nodes_snap[n] = {
                "type": d.get("type", "unknown"),
                "capacity": cap,
                "current_load": load,
                "load_factor": round(load / cap if cap > 0 else 0.0, 4),
                "blocked": d.get("blocked", False),
                "pos": d.get("pos", (500, 400)),
                "label": d.get("label", n)
            }
        edges_snap = [(u, v, d.get("weight", 1.0)) for u, v, d in self.graph.edges(data=True)]
        return {"nodes": nodes_snap, "edges": edges_snap}


if __name__ == "__main__":
    chepauk = ChepaukLayout()
    state = chepauk.get_state()
    print(f"Chepauk layout initialized with {len(state['nodes'])} nodes and {len(state['edges'])} edges.")
    print("Gate 1 Position:", chepauk.get_pixel_pos("Gate_1_Wallajah"))

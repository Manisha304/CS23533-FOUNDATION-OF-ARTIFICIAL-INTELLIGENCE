"""
stadium_twin/crowd.py
=====================
Crowd Animation & Sprite Movement Engine.

Renders hundreds of individual live crowd "Person" sprites moving smoothly along stadium pathways.
Implements linear interpolation path-following and dynamic path reassignment when the Coordinator
issues new rerouting or evacuation plans.
"""

import math
import random
from typing import Dict, Any, List, Tuple, Optional
import pygame

# Palette of Vibrant Person Sprite Colors by Target Destination
DESTINATION_COLORS = {
    "Anna_Pavilion":        (46, 204, 113),   # Green
    "Pavilion_Stand":       (52, 152, 219),   # Blue
    "P4_Upper_Stand":       (155, 89, 182),   # Purple
    "CD_Stand":             (241, 196, 15),   # Amber
    "MA_Chidambaram_Stand": (230, 126, 34),   # Orange
    "Gate_1_Wallajah":      (52, 73, 94),     # Slate
    "Gate_2_Bells":         (44, 62, 80),     # Dark Slate
    "Gate_3_Pattabiram":    (127, 140, 141),  # Gray
    "Gate_4_Vattaram":      (149, 165, 166),  # Light Gray
    "Emergency_Exit":       (231, 76, 60)     # Crimson Red
}
DEFAULT_PERSON_COLOR = (56, 189, 248)  # Cyan


class Person:
    """
    Individual crowd spectator sprite moving along path waypoints.
    """

    def __init__(self, start_pos: Tuple[float, float], path: List[str], layout: Any):
        """
        Initialize Person sprite.

        Args:
            start_pos: Initial (x, y) float canvas position.
            path: List of waypoint node IDs from RouteAgent.
            layout: ChepaukLayout instance.
        """
        # Add slight random offset (+/- 8px) so sprites don't stack in a single line
        self.x = float(start_pos[0] + random.uniform(-8, 8))
        self.y = float(start_pos[1] + random.uniform(-8, 8))

        self.path = path if path else []
        self.path_index = 0
        self.layout = layout

        # Random speed variation (1.5 to 2.8 px/frame) for natural movement
        self.speed = random.uniform(1.5, 2.8)
        self.radius = random.randint(4, 6)

        # Set color based on destination
        dest = path[-1] if path else "default"
        self.color = DESTINATION_COLORS.get(dest, DEFAULT_PERSON_COLOR)

        self.arrived = False
        self.current_node = path[0] if path else "Gate_1_Wallajah"

    def set_new_path(self, new_path: List[str]):
        """Reassign path mid-motion when Coordinator changes routing."""
        if not new_path:
            return
        self.path = new_path
        self.path_index = 0
        self.arrived = False

        dest = new_path[-1]
        self.color = DESTINATION_COLORS.get(dest, DEFAULT_PERSON_COLOR)

    def update(self, dt: float) -> str:
        """
        Smoothly move person towards current target waypoint.

        Returns:
            Current node ID where person is located/heading.
        """
        if self.arrived or not self.path or self.path_index >= len(self.path):
            self.arrived = True
            return self.current_node

        target_node = self.path[self.path_index]
        target_x, target_y = self.layout.get_pixel_pos(target_node)

        # Calculate vector to target
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)

        # Arrival threshold at waypoint (within 12 pixels)
        if dist < 12.0:
            self.current_node = target_node
            self.path_index += 1
            if self.path_index >= len(self.path):
                self.arrived = True
            return target_node

        # Move towards target waypoint via linear velocity vector
        step = self.speed * (dt * 60.0)  # Normalized to ~60 FPS
        if step > dist:
            step = dist

        self.x += (dx / dist) * step
        self.y += (dy / dist) * step

        return self.current_node

    def draw(self, surface: pygame.Surface):
        """Draw person circular sprite with outer border on Pygame surface."""
        px, py = int(self.x), int(self.y)
        # Outer dark ring
        pygame.draw.circle(surface, (15, 23, 42), (px, py), self.radius + 1)
        # Filled color body
        pygame.draw.circle(surface, self.color, (px, py), self.radius)


class CrowdManager:
    """
    Manages population of ~300-500 Person sprites, handles path reassignments,
    and updates node load tallies for CrowdAgent.
    """

    def __init__(self, layout: Any):
        """Initialize CrowdManager with reference to stadium layout."""
        self.layout = layout
        self.people: List[Person] = []

    def spawn_crowd(
        self,
        count: int,
        start_nodes: List[str],
        reroute_paths: Dict[str, List[str]]
    ):
        """
        Spawns a population of Person sprites at designated start gates/stands.

        Args:
            count: Number of spectator sprites to create (300 to 500).
            start_nodes: List of valid origin nodes.
            reroute_paths: Dict of origin -> path list from RouteAgent.
        """
        self.people.clear()

        for _ in range(count):
            origin = random.choice(start_nodes)
            path = reroute_paths.get(origin, [origin])

            # Fallback path if origin path not found
            if not path or len(path) == 1:
                path = [origin, "Concourse_North", "Anna_Pavilion"]

            start_pos = self.layout.get_pixel_pos(origin)
            person = Person(start_pos, path, self.layout)
            self.people.append(person)

    def reassign_paths(self, new_reroute_paths: Dict[str, List[str]], blocked_nodes: List[str]):
        """
        Visibly redirects active crowd sprites toward new safe destinations.
        Called whenever the Coordinator issues a new Action Plan.

        Args:
            new_reroute_paths: Dict of origin -> path list.
            blocked_nodes: List of impassable node IDs.
        """
        blocked_set = set(blocked_nodes)

        for person in self.people:
            current = person.current_node

            # If person is heading toward or located at a blocked zone, reassign immediately!
            if current in blocked_set or (person.path and person.path[-1] in blocked_set):
                # Find path from current node or nearest origin
                new_path = new_reroute_paths.get(current)
                if not new_path:
                    # Fallback to any valid reroute path
                    for alt_origin, alt_path in new_reroute_paths.items():
                        if alt_path and alt_path[-1] not in blocked_set:
                            new_path = [current] + alt_path
                            break
                if new_path:
                    person.set_new_path(new_path)

            elif current in new_reroute_paths:
                new_path = new_reroute_paths[current]
                person.set_new_path(new_path)

    def update(self, dt: float):
        """
        Updates positions of all crowd sprites and synchronizes node loads in ChepaukLayout graph.
        """
        # Tally node loads
        node_counts = {node: 0 for node in self.layout.graph.nodes}

        for person in self.people:
            curr_node = person.update(dt)
            if curr_node in node_counts:
                # Scale sprite count to realistic spectator load (1 sprite = ~25 people)
                node_counts[curr_node] += 25

        # Update node loads in layout graph
        for node_id, load_val in node_counts.items():
            self.layout.set_load(node_id, load_val)

    def draw(self, surface: pygame.Surface):
        """Draw all active Person sprites."""
        for person in self.people:
            person.draw(surface)


if __name__ == "__main__":
    print("CrowdManager module loaded successfully.")

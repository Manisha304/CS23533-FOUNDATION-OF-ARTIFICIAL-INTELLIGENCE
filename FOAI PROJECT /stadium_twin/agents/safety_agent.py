"""
stadium_twin/agents/safety_agent.py
===================================
Safety Agent Module.

Role in Multi-Agent Architecture:
- Emergency Detection & Critical Overriding Agent.
- Manages real-time safety hazards, fires, structural issues, or medical emergencies.

Classical AI Concepts:
- Priority Queue (Max-Heap using heapq with negative severity keys).
- Hard-Constraint Evacuation Directives (Overriding normal traffic policies).
"""

import heapq
from typing import Dict, Any, List, Optional, Tuple

# Severity Levels
SEVERITY_LOW = 1
SEVERITY_MEDIUM = 2
SEVERITY_HIGH = 3
SEVERITY_SEVERE = 4
SEVERITY_CRITICAL = 5


class SafetyAgent:
    """
    Manages priority queue of stadium emergency events and generates evacuation directives.
    """

    def __init__(self):
        """Initialize max-heap priority queue using Python's heapq."""
        # Heap elements: (-severity, sequence_counter, event_dict)
        self.priority_queue: List[Tuple[int, int, Dict[str, Any]]] = []
        self._counter = 0  # Tie-breaker for insertion order stability

    def add_emergency(self, node: str, severity: int, description: str = "") -> Dict[str, Any]:
        """
        Add a safety emergency to the priority queue.

        Args:
            node: Stadium node ID where emergency occurred.
            severity: Integer 1 (Low) to 5 (Critical).
            description: Human readable hazard description.

        Returns:
            dict of created emergency event.
        """
        severity = max(1, min(5, severity))  # Clamp between 1 and 5
        self._counter += 1

        event = {
            "id": f"EMG_{self._counter}",
            "node": node,
            "severity": severity,
            "description": description or f"Level {severity} Hazard at {node}"
        }

        # Use negative severity so heapq behaves as a Max-Heap (5 comes before 1)
        heapq.heappush(self.priority_queue, (-severity, self._counter, event))
        return event

    def is_active(self) -> bool:
        """Check if there are any pending/active emergencies in the queue."""
        return len(self.priority_queue) > 0

    def peek_highest_emergency(self) -> Optional[Dict[str, Any]]:
        """View highest priority emergency without removing it from queue."""
        if not self.priority_queue:
            return None
        return self.priority_queue[0][2]

    def get_next_emergency(self) -> Optional[Dict[str, Any]]:
        """Pop and return the highest priority emergency event from queue."""
        if not self.priority_queue:
            return None
        neg_sev, count, event = heapq.heappop(self.priority_queue)
        return event

    def clear_emergencies(self) -> None:
        """Clear all active emergencies."""
        self.priority_queue.clear()

    def get_evacuation_directive(self) -> Optional[Dict[str, Any]]:
        """
        Generates an evacuation directive based on the highest severity active emergency.

        Evacuation Policy:
        - Emergency zone is marked as structurally BLOCKED.
        - Target destination forced to 'Emergency_Exit'.
        - System status escalated to 'EVACUATION'.

        Returns:
            dict containing evacuation parameters, or None if no active emergency.
        """
        highest_event = self.peek_highest_emergency()
        if not highest_event:
            return None

        return {
            "status": "EVACUATION",
            "emergency_node": highest_event["node"],
            "severity": highest_event["severity"],
            "description": highest_event["description"],
            "forced_target": "Emergency_Exit",
            "blocked_nodes": [highest_event["node"]]
        }


if __name__ == "__main__":
    safety = SafetyAgent()
    safety.add_emergency("Zone_1", 2, "Minor smoke alert")
    safety.add_emergency("Zone_3", 5, "Critical structural hazard")

    print("Is Active?", safety.is_active())
    print("Highest Priority Event (Peek):", safety.peek_highest_emergency())
    print("Evacuation Directive:", safety.get_evacuation_directive())

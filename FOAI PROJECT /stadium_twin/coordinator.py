"""
stadium_twin/coordinator.py
===========================
Coordinator Module for Chepauk StadiumTwin.

Role in Multi-Agent Architecture:
- Central Meta-Controller & Decision Engine.
- Merges agent outputs (CrowdAgent, RouteAgent, SafetyAgent).
- Implements an explicit, rule-based expert hierarchy.
- Directly triggers CrowdManager.reassign_paths(...) so live crowd sprites bend toward safe routes.
"""

from typing import Dict, Any, List, Optional
from stadium_twin.agents.crowd_agent import CrowdAgent
from stadium_twin.agents.route_agent import RouteAgent
from stadium_twin.agents.safety_agent import SafetyAgent


class Coordinator:
    """
    Central Coordinator managing multi-agent decision evaluation.
    """

    def __init__(self, crowd_agent: CrowdAgent, route_agent: RouteAgent, safety_agent: SafetyAgent):
        """Initialize Coordinator with references to active agent suite."""
        self.crowd_agent = crowd_agent
        self.route_agent = route_agent
        self.safety_agent = safety_agent

    def evaluate(self, layout: Any, crowd_manager: Optional[Any] = None) -> Dict[str, Any]:
        """
        Runs agent evaluation cycle and issues actionable plan.

        Args:
            layout: ChepaukLayout instance.
            crowd_manager: Optional CrowdManager instance for triggering live sprite path reassignments.

        Returns:
            action_plan dict.
        """
        graph_state = layout.get_state()
        decision_trace: List[str] = []

        # -------------------------------------------------------------
        # Step 1: Collect CrowdAgent Observations
        # -------------------------------------------------------------
        node_statuses, overloaded_nodes = self.crowd_agent.analyze(graph_state)
        graph_blocked = [n for n, data in graph_state["nodes"].items() if data["blocked"]]

        decision_trace.append(f"[Crowd Agent] Monitored {len(graph_state['nodes'])} Chepauk zones.")
        if overloaded_nodes:
            top_ov = overloaded_nodes[0]
            decision_trace.append(
                f"[Crowd Agent] OVERLOAD! {top_ov['node']} at {top_ov['load_factor']*100:.1f}% capacity."
            )
        else:
            decision_trace.append("[Crowd Agent] All zones operating within safe parameters.")

        if graph_blocked:
            decision_trace.append(f"[Crowd Agent] Impassable closures: {graph_blocked}")

        # -------------------------------------------------------------
        # RULE 1: Safety Emergency Override (Highest Priority)
        # -------------------------------------------------------------
        if self.safety_agent.is_active():
            directive = self.safety_agent.get_evacuation_directive()
            emergency_node = directive["emergency_node"]
            forced_target = directive["forced_target"]

            decision_trace.append(
                f"[Safety Agent] CRITICAL OVERRIDE! Fire/Hazard at {emergency_node} "
                f"(Severity: {directive['severity']}/5 - {directive['description']})."
            )

            all_blocked = list(set(graph_blocked + directive["blocked_nodes"]))

            # Evacuation origins: all seating stands & concourses
            origins = [
                "Anna_Pavilion", "Pavilion_Stand", "P4_Upper_Stand", "CD_Stand",
                "MA_Chidambaram_Stand", "Concourse_North", "Concourse_South",
                "Junction_West", "Junction_East"
            ]

            reroute_res = self.route_agent.reroute(
                stadium_graph=layout,
                blocked_or_overloaded_nodes=all_blocked,
                target_nodes=[forced_target],
                origin_nodes=origins
            )

            decision_trace.append(
                f"[Route Agent] Evacuation paths computed to '{forced_target}' avoiding {all_blocked}."
            )
            decision_trace.append(f"[Coordinator] Action: EVACUATION directive issued.")

            # Trigger live sprite path reassignment
            if crowd_manager:
                crowd_manager.reassign_paths(reroute_res["reroute_paths"], all_blocked)

            return {
                "status": "EVACUATION",
                "blocked_nodes": all_blocked,
                "emergency_node": emergency_node,
                "reroute_paths": reroute_res["reroute_paths"],
                "target_node": forced_target,
                "message": f"[ALERT] Emergency at {emergency_node} — evacuating crowd via {forced_target}!",
                "decision_trace": decision_trace,
                "node_statuses": node_statuses
            }

        # -------------------------------------------------------------
        # RULE 2: Congestion Rerouting / Diversion
        # -------------------------------------------------------------
        overloaded_node_ids = [item["node"] for item in overloaded_nodes]
        all_avoid_nodes = list(set(graph_blocked + overloaded_node_ids))

        if overloaded_nodes or graph_blocked:
            decision_trace.append(f"[Coordinator] Congestion rule triggered. Avoiding: {all_avoid_nodes}.")

            # Identify valid destination gates
            all_gates = ["Gate_1_Wallajah", "Gate_2_Bells", "Gate_3_Pattabiram", "Gate_4_Vattaram"]
            valid_gates = [
                g for g in all_gates
                if g not in all_avoid_nodes and not graph_state["nodes"][g]["blocked"]
            ]

            if not valid_gates:
                # Pick least loaded gate as fallback
                gate_loads = [(g, graph_state["nodes"][g]["load_factor"]) for g in all_gates]
                gate_loads.sort(key=lambda x: x[1])
                valid_gates = [gate_loads[0][0]]

            # Sort valid gates by ascending load
            valid_gates.sort(key=lambda g: graph_state["nodes"][g]["load_factor"])

            origins = [
                "Anna_Pavilion", "Pavilion_Stand", "P4_Upper_Stand", "CD_Stand",
                "MA_Chidambaram_Stand"
            ] + overloaded_node_ids
            origins = list(set(origins))

            reroute_res = self.route_agent.reroute(
                stadium_graph=layout,
                blocked_or_overloaded_nodes=all_avoid_nodes,
                target_nodes=valid_gates,
                origin_nodes=origins
            )

            primary_target = valid_gates[0]
            decision_trace.append(f"[Route Agent] Rerouting crowd toward {primary_target}.")
            decision_trace.append(f"[Coordinator] Action: REROUTE diversion active.")

            # Trigger live sprite path reassignment
            if crowd_manager:
                crowd_manager.reassign_paths(reroute_res["reroute_paths"], all_avoid_nodes)

            return {
                "status": "REROUTE",
                "blocked_nodes": all_avoid_nodes,
                "emergency_node": None,
                "reroute_paths": reroute_res["reroute_paths"],
                "target_node": primary_target,
                "message": f"[INFO] High load at {all_avoid_nodes} — rerouting crowd to {primary_target}",
                "decision_trace": decision_trace,
                "node_statuses": node_statuses
            }

        # -------------------------------------------------------------
        # RULE 3: Normal Monitoring Mode
        # -------------------------------------------------------------
        decision_trace.append("[Coordinator] All stadium zones operating within normal parameters.")

        return {
            "status": "MONITORING",
            "blocked_nodes": [],
            "emergency_node": None,
            "reroute_paths": {},
            "target_node": "Perimeter Gates",
            "message": "SYSTEM NORMAL: Monitoring crowd density at Chepauk Stadium.",
            "decision_trace": decision_trace,
            "node_statuses": node_statuses
        }


if __name__ == "__main__":
    print("Coordinator module updated for Chepauk layout.")

"""
stadium_twin/simulator.py
=========================
Scenario Simulator Engine for Chepauk Stadium.

Configures stadium scenario conditions and spawns live CrowdManager sprite populations.
Runs continuously frame-by-frame in real-time Pygame loop.

Predefined Scenarios:
1. 'gate_blocked'        : Gate 1 (Wallajah Rd) closed; crowd diverted to Gate 2/4.
2. 'emergency_at_stand'  : Fire hazard at Anna Pavilion requiring evacuation to Emergency Exit.
3. 'high_inflow'         : 30,000 fan IPL arrival stress test across all perimeter gates.
4. 'combo_crisis'        : Multiple simultaneous hazards (Gate 1 closed + Anna Pavilion fire + Inflow).
"""

from typing import Dict, Any, Tuple
from stadium_twin.layout import ChepaukLayout
from stadium_twin.crowd import CrowdManager
from stadium_twin.agents.crowd_agent import CrowdAgent
from stadium_twin.agents.route_agent import RouteAgent
from stadium_twin.agents.safety_agent import SafetyAgent
from stadium_twin.coordinator import Coordinator


class ChepaukSimulator:
    """
    Manages Chepauk digital twin simulation scenarios and sprite crowd spawning.
    """

    def __init__(self):
        """Initialize Chepauk layout, agent suite, and crowd manager."""
        self.layout = ChepaukLayout()
        self.crowd_manager = CrowdManager(self.layout)
        self.crowd_agent = CrowdAgent()
        self.route_agent = RouteAgent()
        self.safety_agent = SafetyAgent()
        self.coordinator = Coordinator(self.crowd_agent, self.route_agent, self.safety_agent)
        self.current_scenario = "normal"

    def reset_to_normal(self):
        """Resets stadium layout, clears emergencies, and spawns normal baseline crowd."""
        self.current_scenario = "normal"
        self.layout.reset_state()
        self.safety_agent.clear_emergencies()

        # Compute normal initial routing
        valid_gates = ["Gate_1_Wallajah", "Gate_2_Bells", "Gate_3_Pattabiram", "Gate_4_Vattaram"]
        target_stands = ["Anna_Pavilion", "Pavilion_Stand", "P4_Upper_Stand", "CD_Stand", "MA_Chidambaram_Stand"]

        reroute_res = self.route_agent.reroute(
            stadium_graph=self.layout,
            blocked_or_overloaded_nodes=[],
            target_nodes=target_stands,
            origin_nodes=valid_gates
        )

        # Spawn 350 spectator sprites
        self.crowd_manager.spawn_crowd(
            count=350,
            start_nodes=valid_gates,
            reroute_paths=reroute_res["reroute_paths"]
        )

    def load_scenario(self, scenario_key: str):
        """Applies a predefined scenario configuration."""
        self.layout.reset_state()
        self.safety_agent.clear_emergencies()
        self.current_scenario = scenario_key

        valid_gates = ["Gate_1_Wallajah", "Gate_2_Bells", "Gate_3_Pattabiram", "Gate_4_Vattaram"]
        stands = ["Anna_Pavilion", "Pavilion_Stand", "P4_Upper_Stand", "CD_Stand", "MA_Chidambaram_Stand"]

        if scenario_key == "gate_blocked":
            # Block Gate 1 (Wallajah Rd)
            self.layout.block_node("Gate_1_Wallajah")
            self.layout.set_load("Gate_1_Wallajah", 2900)  # 96.6% load
            self.layout.set_load("Gate_4_Vattaram", 2600)  # 86.6% load

            reroute_res = self.route_agent.reroute(
                stadium_graph=self.layout,
                blocked_or_overloaded_nodes=["Gate_1_Wallajah"],
                target_nodes=["Gate_2_Bells", "Gate_3_Pattabiram"],
                origin_nodes=["Gate_1_Wallajah", "Gate_4_Vattaram"] + stands
            )
            self.crowd_manager.spawn_crowd(400, ["Gate_1_Wallajah", "Gate_4_Vattaram"], reroute_res["reroute_paths"])

        elif scenario_key == "emergency_at_stand":
            # Fire at Anna Pavilion (North Stand)
            self.layout.set_load("Anna_Pavilion", 4800)  # 96% load
            self.safety_agent.add_emergency(
                node="Anna_Pavilion",
                severity=5,
                description="Fire outbreak at Anna Pavilion North Stand!"
            )
            reroute_res = self.route_agent.reroute(
                stadium_graph=self.layout,
                blocked_or_overloaded_nodes=["Anna_Pavilion"],
                target_nodes=["Emergency_Exit"],
                origin_nodes=["Anna_Pavilion"] + stands
            )
            self.crowd_manager.spawn_crowd(400, ["Anna_Pavilion", "Concourse_North"], reroute_res["reroute_paths"])

        elif scenario_key == "high_inflow":
            # 30,000 Fan Arrival across all gates
            self.layout.set_load("Gate_1_Wallajah", 2950)  # 98.3%
            self.layout.set_load("Gate_2_Bells", 2850)     # 95%
            self.layout.set_load("Gate_3_Pattabiram", 2900) # 96.6%
            self.layout.set_load("Gate_4_Vattaram", 2800) # 93.3%

            reroute_res = self.route_agent.reroute(
                stadium_graph=self.layout,
                blocked_or_overloaded_nodes=["Gate_1_Wallajah", "Gate_2_Bells", "Gate_3_Pattabiram"],
                target_nodes=["Gate_4_Vattaram"],
                origin_nodes=valid_gates
            )
            self.crowd_manager.spawn_crowd(450, valid_gates, reroute_res["reroute_paths"])

        elif scenario_key == "combo_crisis":
            # Blocked Gate 1 + Anna Pavilion Fire + Inflow
            self.layout.block_node("Gate_1_Wallajah")
            self.layout.set_load("Gate_1_Wallajah", 2900)
            self.layout.set_load("Anna_Pavilion", 4900)
            self.safety_agent.add_emergency(
                node="Anna_Pavilion",
                severity=5,
                description="Electrical fire and smoke at Anna Pavilion!"
            )
            reroute_res = self.route_agent.reroute(
                stadium_graph=self.layout,
                blocked_or_overloaded_nodes=["Gate_1_Wallajah", "Anna_Pavilion"],
                target_nodes=["Emergency_Exit"],
                origin_nodes=["Anna_Pavilion", "Gate_1_Wallajah"] + stands
            )
            self.crowd_manager.spawn_crowd(450, ["Anna_Pavilion", "Gate_1_Wallajah"], reroute_res["reroute_paths"])

    def update_frame(self, dt: float) -> Dict[str, Any]:
        """
        Updates frame physics & runs multi-agent Coordinator evaluation.

        Returns:
            action_plan dict.
        """
        # 1. Update crowd sprite positions & recalculate node loads
        self.crowd_manager.update(dt)

        # 2. Evaluate Multi-Agent Coordinator and reassign sprite paths
        action_plan = self.coordinator.evaluate(self.layout, self.crowd_manager)
        return action_plan


if __name__ == "__main__":
    sim = ChepaukSimulator()
    sim.reset_to_normal()
    print("ChepaukSimulator initialized successfully.")

"""
stadium_twin/dashboard.py
=========================
Flask Web Dashboard Backend Server for Chepauk StadiumTwin.

Provides RESTful API endpoints and serves the real-time interactive Chepauk Digital Twin web frontend.
Connects directly to ChepaukLayout, ChepaukSimulator, CrowdAgent, RouteAgent, SafetyAgent, and Coordinator.
"""

import os
import sys
from flask import Flask, render_template, jsonify, request

# Ensure parent path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from stadium_twin.layout import ChepaukLayout
from stadium_twin.agents.crowd_agent import CrowdAgent
from stadium_twin.agents.route_agent import RouteAgent
from stadium_twin.agents.safety_agent import SafetyAgent
from stadium_twin.coordinator import Coordinator
from stadium_twin.simulator import ChepaukSimulator

app = Flask(__name__, template_folder="templates", static_folder="static")

# Global Digital Twin Controller Instances for Chepauk
layout = ChepaukLayout()
crowd_agent = CrowdAgent()
route_agent = RouteAgent()
safety_agent = SafetyAgent()
coordinator = Coordinator(crowd_agent, route_agent, safety_agent)
simulator = ChepaukSimulator()

current_scenario = "normal"


@app.route("/")
def index():
    """Render the main interactive Chepauk dashboard page."""
    return render_template("index.html")


@app.route("/api/state", methods=["GET"])
def get_state():
    """Returns the full digital twin state snapshot, agent evaluations, and action plan."""
    # Update frame simulation step
    action_plan = simulator.update_frame(0.016)
    graph_state = simulator.layout.get_state()

    nodes = graph_state["nodes"]
    total_load = sum(data["current_load"] for data in nodes.values())
    total_capacity = sum(data["capacity"] for data in nodes.values())
    overall_ratio = total_load / total_capacity if total_capacity > 0 else 0.0

    # Find highest load bottleneck node
    sorted_nodes = sorted(nodes.items(), key=lambda item: item[1]["load_factor"], reverse=True)
    peak_node = sorted_nodes[0] if sorted_nodes else ("None", {"load_factor": 0.0, "current_load": 0, "label": "None"})

    return jsonify({
        "scenario": current_scenario,
        "graph_state": graph_state,
        "action_plan": action_plan,
        "kpis": {
            "total_load": total_load,
            "total_capacity": total_capacity,
            "overall_occupancy_pct": round(overall_ratio * 100, 1),
            "peak_node": peak_node[1].get("label", peak_node[0]),
            "peak_node_id": peak_node[0],
            "peak_node_pct": round(peak_node[1]["load_factor"] * 100, 1),
            "active_emergency": simulator.safety_agent.is_active(),
            "emergency_details": simulator.safety_agent.peek_highest_emergency()
        }
    })


@app.route("/api/scenario", methods=["POST"])
def set_scenario():
    """Applies a predefined what-if scenario to the Chepauk digital twin."""
    global current_scenario
    data = request.get_json() or {}
    scenario_name = data.get("scenario", "reset")
    current_scenario = scenario_name

    if scenario_name in ["reset", "normal"]:
        simulator.reset_to_normal()
        action_plan = simulator.update_frame(0.016)
        return jsonify({"status": "success", "message": "Reset to baseline normal monitoring mode.", "action_plan": action_plan})

    try:
        simulator.load_scenario(scenario_name)
        action_plan = simulator.update_frame(0.016)
        return jsonify({
            "status": "success",
            "scenario": scenario_name,
            "action_plan": action_plan
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/node/toggle-block", methods=["POST"])
def toggle_block_node():
    """Toggles structural blockage on a specific Chepauk node."""
    data = request.get_json() or {}
    node_id = data.get("node")

    if not node_id or node_id not in simulator.layout.graph.nodes:
        return jsonify({"status": "error", "message": f"Invalid node '{node_id}'"}), 400

    current_blocked = simulator.layout.graph.nodes[node_id].get("blocked", False)
    if current_blocked:
        simulator.layout.unblock_node(node_id)
        msg = f"Unblocked node '{node_id}'"
    else:
        simulator.layout.block_node(node_id)
        msg = f"Blocked node '{node_id}'"

    action_plan = simulator.update_frame(0.016)
    return jsonify({"status": "success", "message": msg, "blocked": not current_blocked, "action_plan": action_plan})


@app.route("/api/emergency", methods=["POST"])
def add_emergency():
    """Triggers an emergency hazard event at a specific Chepauk stand/gate."""
    data = request.get_json() or {}
    node_id = data.get("node")
    severity = int(data.get("severity", 5))
    description = data.get("description", f"Level {severity} Hazard at {node_id}")

    if not node_id or node_id not in simulator.layout.graph.nodes:
        return jsonify({"status": "error", "message": f"Invalid node '{node_id}'"}), 400

    event = simulator.safety_agent.add_emergency(node_id, severity, description)
    action_plan = simulator.update_frame(0.016)
    return jsonify({"status": "success", "event": event, "action_plan": action_plan})


@app.route("/api/clear-emergencies", methods=["POST"])
def clear_emergencies():
    """Clears all active emergency hazards."""
    simulator.safety_agent.clear_emergencies()
    action_plan = simulator.update_frame(0.016)
    return jsonify({"status": "success", "message": "All emergencies cleared.", "action_plan": action_plan})


def run_dashboard(port: int = 5000, debug: bool = False):
    """Run the Flask Chepauk dashboard server."""
    print("=" * 70)
    print(f"   CHEPAUK STADIUM DIGITAL TWIN WEB DASHBOARD RUNNING")
    print(f"   Open in Browser: http://localhost:{port}")
    print("=" * 70)
    simulator.reset_to_normal()
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    run_dashboard(port=5000)

"""
Live Simulation Test -- StadiumTwin v2
======================================
Proves WITHOUT any network/OSM calls that:
  1. The graph + A* RouteAgent works correctly.
  2. Coordinator scores and picks the best open gate.
  3. Blocking a gate forces A* to reroute to a different gate.
  4. 10 simulation ticks run, agents move, crowd counts accumulate.

Run: python live_sim_test.py
"""

import math, random, sys

sys.path.insert(0, ".")
from app.agents.crowd_agents import SafetyAgent, CrowdAgent, RouteAgent, Coordinator, haversine

# ---------------------------------------------------------------------------
# Build a synthetic 5-node graph (4 gates + 1 center)
#
#   [gate_N]          [gate_E]
#        \           /
#         [center]
#        /           \
#   [gate_W]          [gate_S]
# ---------------------------------------------------------------------------
CENTER = {"id": "center", "lat": 13.0630, "lon": 80.2785, "type": "node"}
GATE_N = {"id": "gate_N", "lat": 13.0648, "lon": 80.2785, "type": "gate", "label": "North Gate"}
GATE_S = {"id": "gate_S", "lat": 13.0612, "lon": 80.2785, "type": "gate", "label": "South Gate"}
GATE_E = {"id": "gate_E", "lat": 13.0630, "lon": 80.2810, "type": "gate", "label": "East Gate"}
GATE_W = {"id": "gate_W", "lat": 13.0630, "lon": 80.2760, "type": "gate", "label": "West Gate"}

def dist(a, b):
    return round(haversine(a["lat"], a["lon"], b["lat"], b["lon"]), 1)

NODES = [CENTER, GATE_N, GATE_S, GATE_E, GATE_W]
LINKS = [
    {"source": "center", "target": "gate_N", "length": dist(CENTER, GATE_N)},
    {"source": "center", "target": "gate_S", "length": dist(CENTER, GATE_S)},
    {"source": "center", "target": "gate_E", "length": dist(CENTER, GATE_E)},
    {"source": "center", "target": "gate_W", "length": dist(CENTER, GATE_W)},
]
GRAPH_JSON = {"nodes": NODES, "links": LINKS}
GATES_LIST = [GATE_N, GATE_S, GATE_E, GATE_W]

SPAWN_LAT = 13.0632
SPAWN_LON = 80.2787

SEP = "=" * 65
SEP2 = "-" * 65


def run_ticks(n_ticks, gates_list, sim_state, graph_json, label=""):
    route_agent = RouteAgent()
    open_ids = [g["id"] for g in gates_list
                if sim_state["gate_status"].get(g["id"]) == "open"]

    print("\n" + SEP)
    print("  " + label)
    print("  Open gates: " + str(open_ids))
    print(SEP)

    for tick in range(1, n_ticks + 1):
        off_lat = SPAWN_LAT + random.uniform(-0.0005, 0.0005)
        off_lon = SPAWN_LON + random.uniform(-0.0005, 0.0005)

        blocked_nodes = set(g["id"] for g in gates_list
                            if sim_state["gate_status"].get(g["id"]) == "blocked")

        result = route_agent.astar(graph_json, off_lat, off_lon, open_ids,
                                   blocked_nodes=blocked_nodes)

        if "error" in result:
            print("  Tick %02d: FAIL %s" % (tick, result["error"]))
            continue

        gate = result["gate_id"]
        dist_m = result["distance_m"]
        hops = result["node_count"]
        sim_state["crowd"][gate] = sim_state["crowd"].get(gate, 0) + 1
        print("  Tick %02d: agent -> %-8s  dist=%7.1fm  hops=%d  [crowd@gate: %d]" % (
            tick, gate, dist_m, hops, sim_state["crowd"][gate]))

    print(SEP2)
    print("  Final crowd counts: " + str(sim_state["crowd"]))
    return sim_state


# ---------------------------------------------------------------------------
# PHASE A: Normal -- 10 ticks, all 4 gates open
# ---------------------------------------------------------------------------
random.seed(42)
sim_state_A = {
    "gate_status": {g["id"]: "open" for g in GATES_LIST},
    "crowd": {}
}
sim_state_A = run_ticks(10, GATES_LIST, sim_state_A, GRAPH_JSON,
                        label="PHASE A -- 10 ticks, ALL 4 gates OPEN")

# ---------------------------------------------------------------------------
# PHASE B: Block gate_N -- prove reroute
# ---------------------------------------------------------------------------
sim_state_B = {
    "gate_status": {g["id"]: "open" for g in GATES_LIST},
    "crowd": {}
}
sim_state_B["gate_status"]["gate_N"] = "blocked"
sim_state_B = run_ticks(10, GATES_LIST, sim_state_B, GRAPH_JSON,
                        label="PHASE B -- gate_N BLOCKED => must reroute")

# ---------------------------------------------------------------------------
# Verify reroute
# ---------------------------------------------------------------------------
print("\n" + SEP)
print("  VERIFICATION")
print(SEP)

phase_a_used_n = sim_state_A["crowd"].get("gate_N", 0)
phase_b_used_n = sim_state_B["crowd"].get("gate_N", 0)

print("  Phase A: gate_N received %d agents  (expected > 0)" % phase_a_used_n)
print("  Phase B: gate_N received %d agents  (expected = 0, it's BLOCKED)" % phase_b_used_n)

assert phase_a_used_n > 0, "FAIL: gate_N should have received agents in Phase A"
assert phase_b_used_n == 0, "FAIL: gate_N was blocked but received %d agents" % phase_b_used_n
print("\n  [PASS] A* correctly reroutes when gate_N is blocked.")

# ---------------------------------------------------------------------------
# Coordinator utility scoring
# ---------------------------------------------------------------------------
print("\n" + SEP)
print("  COORDINATOR -- Utility-Based Gate Selection")
print(SEP)

safety = SafetyAgent(GATES_LIST)
crowd  = CrowdAgent(GATES_LIST)
route  = RouteAgent()
coord  = Coordinator(safety, crowd, route)

safety.block_gate("gate_N", reason="live_test")
crowd.update_crowd("gate_E", 800)   # near capacity (1000)

result = coord.best_gate(GRAPH_JSON, SPAWN_LAT, SPAWN_LON, GATES_LIST)

print("  Selected gate : " + result["selected_gate"])
print("  Utility score : " + str(result["utility"]))
print("  Distance      : %s m" % result["distance_m"])
print("  Crowd load    : %s%%" % result["crowd_load_pct"])
print("  Reasoning     : " + result["reasoning"])
print()
print("  All gate scores:")
for s in result["all_scores"]:
    print("    %-8s  utility=%.4f  dist=%.0fm  load=%.0f%%" % (
        s["gate"], s["utility"], s["dist_m"], s["load_pct"]))

assert result["selected_gate"] != "gate_N", "FAIL: blocked gate should not be selected"
assert result["selected_gate"] != "gate_E", "FAIL: congested gate_E should lose to others"
print("\n  [PASS] Coordinator avoided blocked (gate_N) and congested (gate_E).")

print("\n" + SEP)
print("  ALL LIVE SIMULATION TESTS PASSED [OK]")
print(SEP)

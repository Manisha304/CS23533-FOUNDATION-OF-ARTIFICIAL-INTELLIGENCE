"""
stadium_twin/visualize.py
=========================
NetworkX + Matplotlib Visualization & Animation Engine.

Role in Digital Twin Architecture:
- Visual rendering layer for stadium graph states, crowd density heatmaps, and routing pathways.
- Generates side-by-side Before vs After static snapshots and smooth FuncAnimation crowd flow interpolations.

Color Palette Standards:
- OK (Normal Load <= 70%)     : Vibrant Green (#2ecc71)
- WARNING (Load 70% - 90%)    : Amber Yellow (#f1c40f)
- OVERLOADED (Load > 90%)     : Alarm Red (#e74c3c)
- BLOCKED / Emergency Zone    : Dark Slate Gray (#34495e) / Crimson (#c0392b)
- REROUTE PATH EDGE           : Deep Electric Blue (#2980b9) with thick line width
"""

import os
from typing import Dict, Any, List, Optional
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation
import networkx as nx

# --- Color Constants ---
COLOR_OK = "#2ecc71"          # Green
COLOR_WARNING = "#f1c40f"     # Yellow
COLOR_OVERLOADED = "#e74c3c"  # Red
COLOR_BLOCKED = "#7f8c8d"     # Gray
COLOR_EMERGENCY = "#9b59b6"   # Purple
COLOR_PATH_EDGE = "#2980b9"   # Electric Blue Edge
COLOR_DEFAULT_EDGE = "#bdc3c7" # Light Gray Edge


def get_node_color(load_factor: float, is_blocked: bool, is_emergency: bool = False) -> str:
    """Helper function to map node metrics to status color."""
    if is_emergency:
        return COLOR_EMERGENCY
    if is_blocked:
        return COLOR_BLOCKED
    if load_factor >= 0.90:
        return COLOR_OVERLOADED
    if load_factor >= 0.70:
        return COLOR_WARNING
    return COLOR_OK


def render_static(
    before_state: Dict[str, Any],
    action_plan: Dict[str, Any],
    after_state: Dict[str, Any],
    title: str = "StadiumTwin Simulation Scenario",
    output_path: Optional[str] = None
) -> None:
    """
    Renders a side-by-side 2-subplot static comparison figure ("Before" vs "After").

    Args:
        before_state: Dict snapshot before agent intervention.
        action_plan: Action plan output from Coordinator.
        after_state: Dict snapshot after crowd redirection.
        title: Overall figure title.
        output_path: If specified, saves plot image as PNG file.
    """
    # Create Matplotlib Figure with 2 subplots side-by-side
    fig, (ax_before, ax_after) = plt.subplots(1, 2, figsize=(18, 8))
    fig.suptitle(f"StadiumTwin Digital Twin: {title}\nStatus: [{action_plan['status']}] - {action_plan['message']}",
                 fontsize=14, fontweight="bold", y=0.98)

    # -------------------------------------------------------------
    # 1. Build NetworkX Graph Structure from State
    # -------------------------------------------------------------
    G = nx.Graph()
    pos = {}
    for node_id, data in before_state["nodes"].items():
        G.add_node(node_id)
        pos[node_id] = data["pos"]

    for u, v, w in before_state["edges"]:
        G.add_edge(u, v, weight=w)

    # Extract active reroute edges from action_plan
    reroute_edges = set()
    reroute_paths = action_plan.get("reroute_paths", {})
    for path in reroute_paths.values():
        if isinstance(path, list) and len(path) > 1:
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                reroute_edges.add((u, v))
                reroute_edges.add((v, u))

    # -------------------------------------------------------------
    # 2. Draw "BEFORE" Subplot
    # -------------------------------------------------------------
    ax_before.set_title("BEFORE Agent Intervention", fontsize=12, fontweight="bold", pad=10)
    
    before_colors = []
    before_labels = {}
    emergency_node = action_plan.get("emergency_node")

    for node in G.nodes():
        ndata = before_state["nodes"][node]
        lf = ndata["load_factor"]
        is_blk = ndata["blocked"]
        is_emg = (node == emergency_node)
        before_colors.append(get_node_color(lf, is_blk, is_emg))
        before_labels[node] = f"{node}\n({int(lf * 100)}%)"

    nx.draw_networkx_nodes(G, pos, ax=ax_before, node_color=before_colors, node_size=2200, edgecolors="black", linewidths=1.5)
    nx.draw_networkx_edges(G, pos, ax=ax_before, edge_color=COLOR_DEFAULT_EDGE, width=1.5)
    nx.draw_networkx_labels(G, pos, labels=before_labels, ax=ax_before, font_size=8, font_weight="bold")
    ax_before.axis("off")

    # -------------------------------------------------------------
    # 3. Draw "AFTER" Subplot (With Highlighted Reroute Paths)
    # -------------------------------------------------------------
    ax_after.set_title("AFTER Reroute & Diversion Plan", fontsize=12, fontweight="bold", pad=10)

    after_colors = []
    after_labels = {}

    for node in G.nodes():
        ndata = after_state["nodes"][node]
        lf = ndata["load_factor"]
        is_blk = ndata["blocked"]
        is_emg = (node == emergency_node)
        after_colors.append(get_node_color(lf, is_blk, is_emg))
        after_labels[node] = f"{node}\n({int(lf * 100)}%)"

    nx.draw_networkx_nodes(G, pos, ax=ax_after, node_color=after_colors, node_size=2200, edgecolors="black", linewidths=1.5)
    
    # Separate default edges vs reroute edges
    normal_edges = [(u, v) for u, v in G.edges() if (u, v) not in reroute_edges and (v, u) not in reroute_edges]
    path_edges = [(u, v) for u, v in G.edges() if (u, v) in reroute_edges or (v, u) in reroute_edges]

    nx.draw_networkx_edges(G, pos, edgelist=normal_edges, ax=ax_after, edge_color=COLOR_DEFAULT_EDGE, width=1.5)
    if path_edges:
        nx.draw_networkx_edges(G, pos, edgelist=path_edges, ax=ax_after, edge_color=COLOR_PATH_EDGE, width=3.5, style="dashed")

    nx.draw_networkx_labels(G, pos, labels=after_labels, ax=ax_after, font_size=8, font_weight="bold")
    ax_after.axis("off")

    # -------------------------------------------------------------
    # 4. Add Legend for Status Color Indicators
    # -------------------------------------------------------------
    legend_patches = [
        mpatches.Patch(color=COLOR_OK, label="OK (<=70%)"),
        mpatches.Patch(color=COLOR_WARNING, label="WARNING (70%-90%)"),
        mpatches.Patch(color=COLOR_OVERLOADED, label="OVERLOADED (>90%)"),
        mpatches.Patch(color=COLOR_BLOCKED, label="BLOCKED Zone"),
        mpatches.Patch(color=COLOR_EMERGENCY, label="EMERGENCY Hazard"),
        mpatches.Patch(color=COLOR_PATH_EDGE, label="Active Reroute Path")
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=6, bbox_to_anchor=(0.5, 0.02), fontsize=10)

    plt.tight_layout(rect=[0, 0.07, 1, 0.94])

    # Save PNG if output_path specified
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"[Visualize] Saved figure to '{output_path}'.")

    # Show figure non-blocking or blocking depending on environment
    plt.show(block=False)
    plt.pause(1.0)
    plt.close(fig)


def animate_transition(
    before_state: Dict[str, Any],
    after_state: Dict[str, Any],
    action_plan: Dict[str, Any],
    title: str = "Crowd Flow Transition Animation",
    frames: int = 30,
    interval_ms: int = 70,
    save_path: Optional[str] = None
) -> None:
    """
    Interpolates crowd load transition over ~2 seconds using FuncAnimation.

    Args:
        before_state: Initial state dict.
        after_state: Post-action state dict.
        action_plan: Action plan details.
        title: Title of animation.
        frames: Number of animation frames (30 frames @ 70ms = 2.1 sec).
        interval_ms: Time between frames in milliseconds.
        save_path: Optional output path (e.g. output/transition.gif).
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.suptitle(f"StadiumTwin Dynamic Transition: {title}", fontsize=13, fontweight="bold")

    G = nx.Graph()
    pos = {}
    for node_id, data in before_state["nodes"].items():
        G.add_node(node_id)
        pos[node_id] = data["pos"]

    for u, v, w in before_state["edges"]:
        G.add_edge(u, v, weight=w)

    def update_frame(frame_idx: int):
        ax.clear()
        alpha = frame_idx / (frames - 1)  # Linear interpolation factor 0.0 -> 1.0

        node_colors = []
        node_labels = {}
        emergency_node = action_plan.get("emergency_node")

        for node in G.nodes():
            b_load = before_state["nodes"][node]["current_load"]
            a_load = after_state["nodes"][node]["current_load"]
            cap = before_state["nodes"][node]["capacity"]
            is_blk = before_state["nodes"][node]["blocked"] or after_state["nodes"][node]["blocked"]

            interp_load = b_load + alpha * (a_load - b_load)
            interp_lf = interp_load / cap if cap > 0 else 0.0

            is_emg = (node == emergency_node)
            node_colors.append(get_node_color(interp_lf, is_blk, is_emg))
            node_labels[node] = f"{node}\n({int(interp_lf * 100)}%)"

        ax.set_title(f"Transition Progress: {int(alpha * 100)}%", fontsize=11)
        nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=2400, edgecolors="black", linewidths=1.5)
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color=COLOR_DEFAULT_EDGE, width=1.5)
        nx.draw_networkx_labels(G, pos, labels=node_labels, ax=ax, font_size=8, font_weight="bold")
        ax.axis("off")

    anim = FuncAnimation(fig, update_frame, frames=frames, interval=interval_ms, repeat=False)

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        try:
            anim.save(save_path, writer="pillow", fps=15)
            print(f"[Visualize] Saved animation to '{save_path}'.")
        except Exception as e:
            print(f"[Visualize] Could not save animation GIF: {e}")

    plt.show(block=False)
    plt.pause(1.5)
    plt.close(fig)


if __name__ == "__main__":
    from stadium_twin.simulator import StadiumSimulator

    sim = StadiumSimulator()
    b, p, a = sim.run_scenario("gate_a_blocked")
    render_static(b, p, a, title="Gate A Blocked Test", output_path="output/test_gate_a_blocked.png")
    print("Static rendering test complete.")

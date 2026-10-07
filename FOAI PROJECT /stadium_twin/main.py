"""
stadium_twin/main.py
====================
Main Pygame Entry Point for Chepauk StadiumTwin.

Role in Project:
- Runs 1000x800 Pygame real-time event loop at 60 FPS.
- Renders realistic MA Chidambaram Stadium (Chepauk) top-down layout, 300-500 live moving crowd sprites, and HUD overlay.
- Handles keyboard hotkeys ([1-4] scenarios, [R] reset) to trigger live digital twin interventions.
- Demonstrates classical AI multi-agent algorithms with full explainability for viva presentation.
"""

import sys
import os
import pygame

# Ensure parent directory in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from stadium_twin.simulator import ChepaukSimulator
from stadium_twin.renderer import ChepaukRenderer


def print_viva_console_trace(scenario_name: str, action_plan: dict):
    """Prints Coordinator decision trace to console for viva explainability."""
    print("\n" + "=" * 70)
    print(f"  CHEPAUK STADIUM TWIN — LIVE SCENARIO: '{scenario_name.upper()}'")
    print("=" * 70)
    for line in action_plan.get("decision_trace", []):
        print(f"  {line}")
    print("-" * 70)
    print(f"  STATUS      : {action_plan['status']}")
    print(f"  DIRECTIVE   : {action_plan['message']}")
    print(f"  TARGET NODE : {action_plan['target_node']}")
    print("=" * 70 + "\n")


def main():
    """Main Pygame Loop."""
    pygame.init()
    pygame.display.set_caption("StadiumTwin — MA Chidambaram Stadium (Chepauk) Crowd Management Digital Twin")

    screen = pygame.display.set_mode((1000, 800))
    clock = pygame.time.Clock()

    simulator = ChepaukSimulator()
    renderer = ChepaukRenderer(1000, 800)

    # Initialize baseline normal crowd flow
    simulator.reset_to_normal()
    action_plan = simulator.update_frame(0.016)

    print("=" * 70)
    print("   STADIUM TWIN — MA CHIDAMBARAM STADIUM (CHEPAUK) DIGITAL TWIN")
    print("   Real-Time Pygame 2D Simulation Engine & Multi-Agent AI System")
    print("=" * 70)
    print("   CONTROLS:")
    print("     [1] - Scenario 1: Gate 1 Wallajah Closed (Congestion Reroute)")
    print("     [2] - Scenario 2: Emergency at Anna Pavilion (Fire Evacuation)")
    print("     [3] - Scenario 3: High Inflow (30,000 Fan Arrival Stress Test)")
    print("     [4] - Scenario 4: Combo Crisis (Blocked Gate + Fire + Inflow)")
    print("     [R] - Reset to Baseline Normal Flow")
    print("     [ESC / Q] - Exit Simulation")
    print("=" * 70)

    running = True
    frame_count = 0

    while running:
        dt = clock.tick(60) / 1000.0  # Frame delta time in seconds (~0.016s)
        frame_count += 1

        # -------------------------------------------------------------
        # Event Processing
        # -------------------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False

                elif event.key == pygame.K_1:
                    print("\n[Hotkey 1] Triggering Gate 1 Blocked Scenario...")
                    simulator.load_scenario("gate_blocked")
                    action_plan = simulator.update_frame(dt)
                    print_viva_console_trace("Gate 1 Blocked", action_plan)

                elif event.key == pygame.K_2:
                    print("\n[Hotkey 2] Triggering Anna Pavilion Fire Emergency...")
                    simulator.load_scenario("emergency_at_stand")
                    action_plan = simulator.update_frame(dt)
                    print_viva_console_trace("Anna Pavilion Emergency", action_plan)

                elif event.key == pygame.K_3:
                    print("\n[Hotkey 3] Triggering High Fan Inflow Scenario...")
                    simulator.load_scenario("high_inflow")
                    action_plan = simulator.update_frame(dt)
                    print_viva_console_trace("High Inflow", action_plan)

                elif event.key == pygame.K_4:
                    print("\n[Hotkey 4] Triggering Combo Crisis Scenario...")
                    simulator.load_scenario("combo_crisis")
                    action_plan = simulator.update_frame(dt)
                    print_viva_console_trace("Combo Crisis", action_plan)

                elif event.key == pygame.K_r:
                    print("\n[Hotkey R] Resetting to Normal Flow...")
                    simulator.reset_to_normal()
                    action_plan = simulator.update_frame(dt)
                    print_viva_console_trace("Baseline Reset", action_plan)

        # -------------------------------------------------------------
        # Update Agent Pipeline & Live Crowd Sprites
        # -------------------------------------------------------------
        # Run agent evaluation every 10 frames (~6 times per sec) for smooth 60 FPS
        if frame_count % 10 == 0:
            action_plan = simulator.update_frame(dt)
        else:
            simulator.crowd_manager.update(dt)

        # -------------------------------------------------------------
        # Render Graphics Frame
        # -------------------------------------------------------------
        # 1. Draw Chepauk Top-Down Stadium Layout & Pathways
        renderer.draw_stadium_layout(screen, simulator.layout, action_plan)

        # 2. Draw Live Crowd Person Sprites
        simulator.crowd_manager.draw(screen)

        # 3. Draw Semi-Transparent AI Decision HUD Overlay Panel
        renderer.draw_hud(
            surface=screen,
            action_plan=action_plan,
            scenario_name=simulator.current_scenario,
            total_crowd=len(simulator.crowd_manager.people)
        )

        pygame.display.flip()

    pygame.quit()
    print("\nExiting StadiumTwin Chepauk Simulation. Goodbye!")


if __name__ == "__main__":
    main()

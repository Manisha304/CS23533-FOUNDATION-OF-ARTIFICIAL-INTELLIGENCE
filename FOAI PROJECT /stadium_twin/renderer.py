"""
stadium_twin/renderer.py
========================
Pygame Top-Down Realistic Stadium Renderer & HUD Overlay Engine.

Draws realistic architectural elements of MA Chidambaram Stadium (Chepauk), Chennai:
- Lush Green Cricket Pitch & Crease Lines.
- Curved Seating Bowl with 5 distinct named stands.
- 4 Perimeter Gate Entrances (Wallajah, Bells, Pattabiram, Vattaram).
- Exterior Parking Zone & Red/White Hazard Striped Emergency Exit.
- Live Crowd Sprites (300-500 moving people).
- Highlighted Reroute Path Overlay.
- Semi-transparent HUD Panel displaying live Coordinator decision traces.
"""

import math
from typing import Dict, Any, List, Tuple
import pygame

# Color Palette Definitions
COLOR_BG = (15, 23, 42)               # Dark Slate Background (#0f172a)
COLOR_PITCH_GRASS = (34, 139, 34)     # Forest Green (#228b22)
COLOR_PITCH_INNER = (46, 160, 67)     # Light Field Green
COLOR_CREASE = (240, 240, 240)        # Off-white pitch crease
COLOR_PATHWAY = (51, 65, 85)          # Slate Walkway (#334155)
COLOR_PARKING = (30, 41, 59)          # Dark Parking (#1e293b)
COLOR_CAR = (100, 116, 139)           # Slate Car Icon

# Load Status Colors
STATUS_COLORS = {
    "OK": (46, 204, 113),          # Green
    "WARNING": (241, 196, 15),     # Amber Yellow
    "OVERLOADED": (231, 76, 60),   # Red
    "BLOCKED": (100, 116, 139),    # Gray
    "FIRE_HAZARD": (155, 89, 182)  # Purple
}

# UI Fonts & HUD Colors
HUD_BG = (11, 17, 30, 220)            # Semi-transparent dark slate (RGBA)
HUD_BORDER = (56, 189, 248, 100)
COLOR_REROUTE_LINE = (37, 99, 235)     # Deep Electric Blue


class ChepaukRenderer:
    """
    Renders realistic Chepauk stadium layout, live crowd sprites, and HUD overlay on Pygame surface.
    """

    def __init__(self, width: int = 1000, height: int = 800):
        """Initialize renderer surface dimensions and font system."""
        self.width = width
        self.height = height

        # Initialize Pygame fonts
        pygame.font.init()
        self.title_font = pygame.font.SysFont("Outfit,Arial", 18, bold=True)
        self.body_font = pygame.font.SysFont("Outfit,Arial", 13, bold=False)
        self.small_font = pygame.font.SysFont("Consolas,monospace", 11, bold=True)

        # Pre-build Hazard Pattern Surface for Emergency Exit
        self.hazard_stripe = self._create_hazard_stripe_texture(100, 40)
        # Pre-allocate reusable HUD surface to prevent memory leaks in render loop
        self.hud_surface = pygame.Surface((380, 220), pygame.SRCALPHA)

    def _create_hazard_stripe_texture(self, w: int, h: int) -> pygame.Surface:
        """Create red/white diagonal hazard stripe texture surface."""
        surf = pygame.Surface((w, h))
        surf.fill((231, 76, 60))  # Red base
        stripe_color = (255, 255, 255)  # White stripes

        stripe_w = 12
        for x in range(-h, w + h, stripe_w * 2):
            pts = [(x, 0), (x + stripe_w, 0), (x + stripe_w - h, h), (x - h, h)]
            pygame.draw.polygon(surf, stripe_color, pts)

        return surf

    def draw_stadium_layout(self, surface: pygame.Surface, layout: Any, action_plan: Dict[str, Any]):
        """
        Draws the realistic top-down 2D Chepauk stadium elements.
        """
        # 1. Background
        surface.fill(COLOR_BG)

        # 2. Draw Walkway Pathways (Gray strips connecting nodes)
        for u, v, data in layout.graph.edges(data=True):
            p1 = layout.get_pixel_pos(u)
            p2 = layout.get_pixel_pos(v)
            pygame.draw.line(surface, COLOR_PATHWAY, p1, p2, 16)

        # 3. Draw Outer Perimeter Boundary Arc/Ellipse
        pygame.draw.ellipse(surface, (30, 41, 59), (150, 100, 700, 600), 4)

        # 4. Draw Center Cricket Pitch (Lush Green Oval & Pitch Rectangle)
        # Outfield Ground
        pygame.draw.ellipse(surface, COLOR_PITCH_GRASS, (360, 240, 280, 320))
        pygame.draw.ellipse(surface, COLOR_PITCH_INNER, (375, 255, 250, 290))
        # 30-yard Circle Boundary
        pygame.draw.ellipse(surface, (255, 255, 255, 120), (390, 270, 220, 260), 2)
        # Center Pitch Rect
        pitch_rect = pygame.Rect(485, 360, 30, 80)
        pygame.draw.rect(surface, (194, 168, 120), pitch_rect)  # Turf clay color
        pygame.draw.rect(surface, COLOR_CREASE, pitch_rect, 1)

        # 5. Draw Parking Area (West Exterior Zone)
        parking_rect = pygame.Rect(30, 620, 120, 120)
        pygame.draw.rect(surface, COLOR_PARKING, parking_rect, border_radius=8)
        pygame.draw.rect(surface, (71, 85, 105), parking_rect, 2, border_radius=8)
        # Draw "PARKING" label & mini car icons
        txt_p = self.small_font.render("PARKING LOT", True, (148, 163, 184))
        surface.blit(txt_p, (38, 628))
        for car_y in [650, 675, 700]:
            for car_x in [45, 80, 115]:
                pygame.draw.rect(surface, COLOR_CAR, (car_x, car_y, 16, 10), border_radius=2)

        # 6. Draw Emergency Exit (North-East Hazard Striped Box)
        exit_rect = pygame.Rect(810, 60, 110, 45)
        surface.blit(self.hazard_stripe, (810, 60))
        pygame.draw.rect(surface, (255, 255, 255), exit_rect, 3)
        txt_exit = self.small_font.render("EMERGENCY EXIT", True, (0, 0, 0))
        # Draw background pill behind text for legibility
        txt_bg = pygame.Rect(815, 72, 100, 20)
        pygame.draw.rect(surface, (255, 255, 255), txt_bg, border_radius=4)
        surface.blit(txt_exit, (820, 75))

        # 7. Draw Highlighted Active Reroute Paths
        reroute_paths = action_plan.get("reroute_paths", {})
        if reroute_paths:
            for path in reroute_paths.values():
                if isinstance(path, list) and len(path) > 1:
                    for i in range(len(path) - 1):
                        p1 = layout.get_pixel_pos(path[i])
                        p2 = layout.get_pixel_pos(path[i + 1])
                        pygame.draw.line(surface, COLOR_REROUTE_LINE, p1, p2, 6)

        # 8. Draw Seating Stands & Perimeter Gates
        nodes_state = layout.get_state()["nodes"]
        emergency_node = action_plan.get("emergency_node")

        for node_id, data in nodes_state.items():
            pos = data["pos"]
            node_type = data["type"]
            load_factor = data["load_factor"]
            is_blocked = data["blocked"]
            is_emergency = (node_id == emergency_node)

            # Determine color
            if is_emergency:
                fill_color = STATUS_COLORS["FIRE_HAZARD"]
            elif is_blocked:
                fill_color = STATUS_COLORS["BLOCKED"]
            elif load_factor >= 0.90:
                fill_color = STATUS_COLORS["OVERLOADED"]
            elif load_factor >= 0.70:
                fill_color = STATUS_COLORS["WARNING"]
            else:
                fill_color = STATUS_COLORS["OK"]

            # Draw Seating Stands as Curved Rectangles / Rounded Shapes
            if node_type == "stand":
                rect = pygame.Rect(pos[0] - 70, pos[1] - 30, 140, 60)
                # Outer shadow glow
                pygame.draw.rect(surface, fill_color, rect.inflate(6, 6), border_radius=12)
                # Inner dark Stand background
                pygame.draw.rect(surface, (15, 23, 42), rect, border_radius=10)
                pygame.draw.rect(surface, fill_color, rect, 2, border_radius=10)

                # Stand Label & Load Percentage
                label_txt = self.body_font.render(data["label"], True, (255, 255, 255))
                load_txt = self.small_font.render(f"Load: {int(load_factor*100)}%", True, fill_color)

                surface.blit(label_txt, (pos[0] - label_txt.get_width() // 2, pos[1] - 16))
                surface.blit(load_txt, (pos[0] - load_txt.get_width() // 2, pos[1] + 4))

            # Draw Perimeter Gates as Door Rectangles
            elif node_type == "gate":
                g_rect = pygame.Rect(pos[0] - 50, pos[1] - 25, 100, 50)
                pygame.draw.rect(surface, fill_color, g_rect, border_radius=8)
                pygame.draw.rect(surface, (15, 23, 42), g_rect.inflate(-4, -4), border_radius=6)

                lbl = self.small_font.render(data["label"], True, (255, 255, 255))
                stat_lbl = self.small_font.render(f"{int(load_factor*100)}% {('BLOCKED' if is_blocked else '')}", True, fill_color)

                surface.blit(lbl, (pos[0] - lbl.get_width() // 2, pos[1] - 14))
                surface.blit(stat_lbl, (pos[0] - stat_lbl.get_width() // 2, pos[1] + 2))

    def draw_hud(
        self,
        surface: pygame.Surface,
        action_plan: Dict[str, Any],
        scenario_name: str,
        total_crowd: int
    ):
        """
        Draws semi-transparent HUD overlay panel with live Coordinator decisions & control hotkeys.
        """
        hud_surface = self.hud_surface
        hud_surface.fill(HUD_BG)
        pygame.draw.rect(hud_surface, HUD_BORDER, (0, 0, 380, 220), 1, border_radius=12)

        # Header Title
        title_txt = self.title_font.render("CHEPAUK DIGITAL TWIN AI HUD", True, (56, 189, 248))
        hud_surface.blit(title_txt, (14, 12))

        # System Status Badge
        status = action_plan.get("status", "MONITORING")
        status_color = STATUS_COLORS.get("OK" if status == "MONITORING" else ("WARNING" if status == "REROUTE" else "OVERLOADED"))

        badge_rect = pygame.Rect(250, 10, 115, 24)
        pygame.draw.rect(hud_surface, status_color, badge_rect, border_radius=12)
        status_txt = self.small_font.render(status, True, (15, 23, 42))
        hud_surface.blit(status_txt, (250 + (115 - status_txt.get_width()) // 2, 14))

        # Live Coordinator Directive Box
        msg = action_plan.get("message", "Monitoring normal flow.")
        msg_txt = self.body_font.render(f"Coordinator Directive:", True, (241, 196, 15))
        hud_surface.blit(msg_txt, (14, 42))

        # Wrap directive message if long
        words = msg.split(" ")
        line1 = " ".join(words[:6])
        line2 = " ".join(words[6:]) if len(words) > 6 else ""

        txt1 = self.small_font.render(line1, True, (255, 255, 255))
        hud_surface.blit(txt1, (14, 62))
        if line2:
            txt2 = self.small_font.render(line2, True, (255, 255, 255))
            hud_surface.blit(txt2, (14, 76))

        # Crowd Tally & Target
        crowd_txt = self.body_font.render(f"Live Crowd Sprites: {total_crowd} spectators", True, (56, 189, 248))
        hud_surface.blit(crowd_txt, (14, 98))

        target_txt = self.body_font.render(f"Primary Target Node: {action_plan.get('target_node', 'Gates')}", True, (226, 232, 240))
        hud_surface.blit(target_txt, (14, 116))

        # Hotkeys Guide Divider
        pygame.draw.line(hud_surface, (51, 65, 85), (14, 138), (366, 138), 1)

        hk_title = self.small_font.render("SCENARIO HOTKEYS [Press Key 0-4]:", True, (148, 163, 184))
        hud_surface.blit(hk_title, (14, 145))

        k1 = self.small_font.render("[1] Gate 1 Closed   [2] Zone 3 Fire", True, (203, 213, 225))
        k2 = self.small_font.render("[3] High Inflow     [4] Combo Crisis   [R] Reset", True, (203, 213, 225))
        hud_surface.blit(k1, (14, 165))
        hud_surface.blit(k2, (14, 182))

        surface.blit(hud_surface, (15, 15))


if __name__ == "__main__":
    print("ChepaukRenderer module loaded successfully.")

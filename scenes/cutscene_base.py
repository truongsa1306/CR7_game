"""
scenes/cutscene_base.py
=========================
Shared visual scaffold for "Cutscene Mode" scenes (Intro + Level-Up).
Both show: stadium background, the chibi player standing center-stage,
the bottom dialogue box, and (for level-up) a title banner + status
badge + mini algorithm graph. Subclasses just feed in what to show.
"""
import pygame
import config as C
from scenes.base_scene import BaseScene
from ui.panel import draw_stadium_background, draw_outer_frame, draw_wood_panel
from ui.dialogue_box import DialogueBox
from ui.label import draw_text
from entities.player import Player
from systems.audio_manager import AudioManager


class CutsceneScene(BaseScene):
    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.player = Player(kit_index=0)
        self.dialogue = DialogueBox(on_skip=self._on_dialogue_advance)
        self.banner_text = None
        self.badge_lines = None
        self.graph = None  # (title, kind) e.g. ("Hill Climbing", "peak")
        self._next_action = None

    def _on_dialogue_advance(self):
        if self._next_action:
            self._next_action()

    def handle_event(self, event):
        self.dialogue.handle_event(event)

    def update(self, dt):
        self.dialogue.update(dt)
        self.player.update(dt)

    def draw(self, surface):
        draw_stadium_background(surface)

        if self.banner_text:
            self._draw_banner(surface, self.banner_text)

        center = C.CHIBI_PLAYER_RECT.center
        # subtle ground glow under the player
        glow = pygame.Surface((120, 36), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 215, 90, 90), glow.get_rect())
        surface.blit(glow, (center[0] - 60, center[1] + 40))
        self.player.draw_at(surface, center)

        if self.badge_lines:
            self._draw_badge(surface, self.badge_lines)

        if self.graph:
            self._draw_graph(surface, *self.graph)

        self.dialogue.draw(surface)
        draw_outer_frame(surface)

    # ------------------------------------------------------------------
    def _draw_banner(self, surface, text):
        rect = C.CUTSCENE_TITLE_BANNER_RECT
        draw_wood_panel(surface, rect, border=5, corner=10)
        draw_text(surface, text, (rect.centerx, rect.centery - 14), size=26,
                  color=C.COL_GOLD_BRIGHT, align="center")

    def _draw_badge(self, surface, lines):
        rect = C.LEVEL_STATUS_BADGE_RECT
        draw_wood_panel(surface, rect, border=4, corner=8)
        y = rect.top + 8
        for line, size, color in lines:
            h = draw_text(surface, line, (rect.centerx, y), size=size, color=color, align="center")
            y += h + 2

    def _draw_graph(self, surface, title, points):
        rect = C.HEURISTIC_GRAPH_BOX_RECT
        draw_wood_panel(surface, rect, border=4, corner=8)
        draw_text(surface, title, (rect.centerx, rect.top + 6), size=13,
                  color=C.COL_GOLD_BRIGHT, align="center")
        plot_rect = pygame.Rect(rect.left + 10, rect.top + 28, rect.width - 20, rect.height - 38)
        pygame.draw.rect(surface, (20, 26, 18), plot_rect, border_radius=3)
        if len(points) >= 2:
            max_v = max(points) or 1
            step_x = plot_rect.width / (len(points) - 1)
            poly = []
            for i, v in enumerate(points):
                x = plot_rect.left + i * step_x
                y = plot_rect.bottom - (v / max_v) * plot_rect.height
                poly.append((int(x), int(y)))
            fill_poly = poly + [(plot_rect.right, plot_rect.bottom), (plot_rect.left, plot_rect.bottom)]
            pygame.draw.polygon(surface, (90, 160, 90), fill_poly)
            pygame.draw.lines(surface, (180, 230, 150), False, poly, 2)
            peak_i = points.index(max(points))
            pygame.draw.circle(surface, C.COL_GOLD_BRIGHT, (int(poly[peak_i][0]), int(poly[peak_i][1])), 4)

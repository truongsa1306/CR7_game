"""
scenes/levelup_scene.py
=======================
Level transition scene that matches the spec's cutscene/level-up mode:
stadium backdrop, ornate frame, CR7 chibi at center, big "BAN DA LEN CAP!"
title, kit unlock badge, algorithm graph panel, sparkle burst, and the
shared bottom dialogue box.
"""
import math
import random

import pygame

import config as C
from effects.particles import ParticleSystem
from scenes.cutscene_base import CutsceneScene
from systems.audio_manager import AudioManager
from ui.button import Button
from ui.label import draw_text
from ui.panel import draw_outer_frame, draw_stadium_background, draw_wood_panel


GRAPH_THEMES = {
    1: {
        "title": "Informed Search",
        "subtitle": "LOW COST PATH",
        "points": [2, 4, 3, 6, 5, 9, 8],
    },
    2: {
        "title": "Hill Climbing",
        "subtitle": "OPTIMAL FOUND\nLEVEL 2 PEAK",
        "points": [2, 4, 8, 7, 11, 8, 5],
    },
    3: {
        "title": "Gradient Descent",
        "subtitle": "LEVEL 3 PEAK",
        "points": [3, 6, 4, 8, 5, 11, 2],
    },
}


class LevelUpScene(CutsceneScene):
    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.elapsed = 0.0
        self.particles = ParticleSystem()
        self._sparkle_rng = random.Random(7)
        self.back_button = Button(pygame.Rect(20, 20, 80, 28), "BACK", font_size=12,
                                  on_click=self._go_to_level_select)

    def on_enter(self, **kwargs):
        new_level = self.game_state.level
        kit = C.KITS[new_level]

        self.elapsed = 0.0
        self.particles.clear()
        self.player.set_kit(new_level)
        self.banner_text = "BAN DA LEN CAP!"
        self.badge_lines = [
            (f"LEVEL: {new_level}", 16, C.COL_CREAM_TEXT),
            ("New Kit Unlocked:", 13, C.COL_CREAM_TEXT),
            (kit["label"], 16, C.COL_GOLD_BRIGHT),
        ]
        self.graph = GRAPH_THEMES.get(new_level, GRAPH_THEMES[1])
        self.dialogue.set_text(
            C.LEVELUP_LINES.get(new_level, "Tuyet voi! Hay tiep tuc chinh phuc dinh cao tiep theo."),
            kit_index=new_level,
        )
        self._next_action = self._go_to_gameplay
        self._emit_levelup_sparkles()
        AudioManager.instance().play_sfx("level_up")

    def update(self, dt):
        super().update(dt)
        self.elapsed += dt
        self.particles.update(dt)
        if int((self.elapsed - dt) * 3) != int(self.elapsed * 3):
            self._emit_levelup_sparkles(count=8)

    def draw(self, surface):
        draw_stadium_background(surface)
        self._draw_gold_sparkles(surface)
        self._draw_title(surface)
        self._draw_player_stage(surface)
        self._draw_status_badge(surface)
        self._draw_algorithm_graph(surface)
        self.particles.draw(surface)
        self.dialogue.draw(surface)
        self.back_button.draw(surface)
        draw_outer_frame(surface)

    def handle_event(self, event):
        super().handle_event(event)
        self.back_button.handle_event(event)

    def _go_to_level_select(self):
        self.manager.change(C.STATE_LEVEL_SELECT)

    def _go_to_gameplay(self):
        if self.game_state.level == 4:
            self.manager.change(C.STATE_CARO)
        elif self.game_state.level == 5:
            self.manager.change(C.STATE_EIGHT_QUEENS)
        else:
            self.manager.change(C.STATE_GAMEPLAY)

    # ------------------------------------------------------------------
    def _emit_levelup_sparkles(self, count=34):
        center = C.CHIBI_PLAYER_RECT.center
        for _ in range(count):
            x = center[0] + self._sparkle_rng.uniform(-170, 220)
            y = center[1] + self._sparkle_rng.uniform(-120, 35)
            self.particles.emit_sparkle_burst(
                (x, y),
                count=1,
                speed=self._sparkle_rng.uniform(12, 42),
                life=self._sparkle_rng.uniform(0.75, 1.4),
            )

    def _draw_gold_sparkles(self, surface):
        for i in range(18):
            phase = self.elapsed * 2.2 + i * 1.7
            x = 190 + (i * 43) % 650
            y = 72 + (i * 31) % 210
            scale = 4 + int(3 * (0.5 + 0.5 * math.sin(phase)))
            color = C.COL_GOLD_BRIGHT if i % 3 else C.COL_WHITE
            pygame.draw.line(surface, color, (x - scale, y), (x + scale, y), 2)
            pygame.draw.line(surface, color, (x, y - scale), (x, y + scale), 2)

    def _draw_title(self, surface):
        rect = C.CUTSCENE_TITLE_BANNER_RECT
        text_y = rect.top + 4 + int(math.sin(self.elapsed * 3.0) * 2)
        draw_text(surface, self.banner_text, (rect.centerx + 3, text_y + 3),
                  size=34, color=(70, 38, 20), align="center", shadow=False)
        draw_text(surface, self.banner_text, (rect.centerx, text_y),
                  size=34, color=C.COL_GOLD_BRIGHT, align="center", shadow=True)

    def _draw_player_stage(self, surface):
        center = C.CHIBI_PLAYER_RECT.center
        pulse = 0.5 + 0.5 * math.sin(self.elapsed * 5.0)
        glow = pygame.Surface((150, 54), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 230, 100, 70 + int(45 * pulse)), glow.get_rect())
        pygame.draw.ellipse(glow, (255, 255, 190, 120), glow.get_rect().inflate(-34, -20), 3)
        surface.blit(glow, (center[0] - 75, center[1] + 38))
        self.player.draw_at(surface, center)

    def _draw_status_badge(self, surface):
        rect = C.LEVEL_STATUS_BADGE_RECT
        draw_wood_panel(surface, rect, border=4, corner=8, fill=(70, 43, 30))
        y = rect.top + 8
        for line, size, color in self.badge_lines:
            h = draw_text(surface, line, (rect.left + 12, y), size=size, color=color, align="left")
            y += h + 1

    def _draw_algorithm_graph(self, surface):
        rect = C.HEURISTIC_GRAPH_BOX_RECT
        draw_wood_panel(surface, rect, border=4, corner=8, fill=(54, 32, 24))

        title = self.graph["title"]
        subtitle = self.graph["subtitle"]
        points = self.graph["points"]

        draw_text(surface, title, (rect.centerx, rect.top + 8),
                  size=13, color=C.COL_GOLD_BRIGHT, align="center")
        sub_y = rect.top + 29
        for line in subtitle.split("\n"):
            draw_text(surface, line, (rect.centerx, sub_y), size=9,
                      color=C.COL_CREAM_TEXT, align="center", shadow=False)
            sub_y += 12

        plot_rect = pygame.Rect(rect.left + 14, rect.top + 60, rect.width - 28, rect.height - 72)
        pygame.draw.rect(surface, (20, 28, 18), plot_rect, border_radius=3)
        max_v = max(points) or 1
        step_x = plot_rect.width / (len(points) - 1)
        poly = []
        for i, value in enumerate(points):
            x = plot_rect.left + i * step_x
            y = plot_rect.bottom - (value / max_v) * plot_rect.height
            poly.append((int(x), int(y)))

        fill_poly = poly + [(plot_rect.right, plot_rect.bottom), (plot_rect.left, plot_rect.bottom)]
        pygame.draw.polygon(surface, (72, 145, 72), fill_poly)
        pygame.draw.lines(surface, (210, 240, 165), False, poly, 3)
        peak = poly[points.index(max(points))]
        pygame.draw.circle(surface, C.COL_GOLD_BRIGHT, (int(peak[0]), int(peak[1])), 4)

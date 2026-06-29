"""
scenes/level_select_scene.py
============================
Simple level-selection menu shown right after the intro scene.
"""
import pygame

import config as C
from scenes.base_scene import BaseScene
from systems.asset_manager import AssetManager, placeholder_trophy
from ui.button import Button
from ui.label import draw_text
from ui.panel import draw_outer_frame, draw_wood_panel


class LevelSelectScene(BaseScene):
    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.buttons = []

    def on_enter(self, **kwargs):
        self.buttons = []
        panel = pygame.Rect(180, 100, 664, 360)
        button_w = 220
        button_h = 48
        start_x = panel.centerx - button_w // 2
        y = panel.top + 110
        for level in sorted(C.LEVEL_NAMES.keys()):
            rect = pygame.Rect(start_x, y + level * 70, button_w, button_h)
            self.buttons.append(
                Button(rect, f"Man {level + 1}: {C.LEVEL_NAMES[level]}", font_size=13,
                       on_click=lambda lvl=level: self._start_level(lvl))
            )

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((20, 24, 20))
        draw_wood_panel(surface, pygame.Rect(140, 70, 744, 430), border=6, corner=10, fill=(58, 35, 24))
        draw_text(surface, "CHON MAN CHOI", (512, 120), size=28, color=C.COL_CREAM_TEXT, align="center")
        draw_text(surface, "Chon man de bat dau", (512, 160), size=16, color=C.COL_CREAM_TEXT, align="center")

        for button in self.buttons:
            button.draw(surface)

        draw_outer_frame(surface)

    def _start_level(self, level):
        self.game_state.level = level
        self.game_state.kit_index = level
        self.game_state.reset_energy()
        self.manager.change(C.STATE_GAMEPLAY)

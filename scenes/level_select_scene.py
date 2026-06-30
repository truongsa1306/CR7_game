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
        self.back_button = Button(pygame.Rect(20, 20, 80, 28), "BACK", font_size=12,
                                  on_click=self._go_to_intro)

    def on_enter(self, **kwargs):
        self.buttons = []
        panel = pygame.Rect(180, 100, 664, 360)
        button_w = 220
        button_h = 48
        gap = 10
        start_x = panel.centerx - button_w // 2
        levels = sorted(C.LEVEL_NAMES.keys())
        total_h = len(levels) * button_h + (len(levels) - 1) * gap
        start_y = panel.top + max(40, (panel.height - total_h) // 2)
        for i, level in enumerate(levels):
            rect = pygame.Rect(start_x, start_y + i * (button_h + gap), button_w, button_h)
            self.buttons.append(
                Button(rect, f"Man {level + 1}: {C.LEVEL_NAMES[level]}", font_size=13,
                       on_click=lambda lvl=level: self._start_level(lvl))
            )

    def handle_event(self, event):
        self.back_button.handle_event(event)
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
        self.back_button.draw(surface)

        draw_outer_frame(surface)

    def _start_level(self, level):
        self.game_state.level = level
        self.game_state.kit_index = level
        if level == 4:
            self.manager.change(C.STATE_CARO)
        elif level == 5:
            self.manager.change(C.STATE_EIGHT_QUEENS)
        else:
            self.manager.change(C.STATE_GAMEPLAY)

    def _go_to_intro(self):
        self.manager.change(C.STATE_INTRO)

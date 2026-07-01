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
        panel = pygame.Rect(140, 90, 744, 390)
        button_w = 300
        button_h = 48
        gap_x = 18
        gap_y = 12
        levels = sorted(C.LEVEL_NAMES.keys())
        columns = 2
        rows = (len(levels) + columns - 1) // columns
        total_w = columns * button_w + gap_x
        total_h = rows * button_h + (rows - 1) * gap_y
        start_x = panel.centerx - total_w // 2
        start_y = panel.top + max(82, (panel.height - total_h) // 2 + 24)
        for i, level in enumerate(levels):
            col = i % columns
            row = i // columns
            rect = pygame.Rect(
                start_x + col * (button_w + gap_x),
                start_y + row * (button_h + gap_y),
                button_w,
                button_h,
            )
            self.buttons.append(
                Button(rect, f"Màn {level + 1}: {C.LEVEL_NAMES[level]}", font_size=12,
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
        draw_wood_panel(surface, pygame.Rect(120, 62, 784, 450), border=6, corner=10, fill=(58, 35, 24))
        draw_text(surface, "CHON MAN CHOI", (512, 120), size=28, color=C.COL_CREAM_TEXT, align="center")
        draw_text(surface, "Chon man de bat dau", (512, 160), size=16, color=C.COL_CREAM_TEXT, align="center")

        for button in self.buttons:
            button.draw(surface)
        self.back_button.draw(surface)

        draw_outer_frame(surface)

    def _start_level(self, level):
        self.game_state.level = level
        self.game_state.kit_index = min(level, max(C.KITS.keys()))
        if level == 3:
            self.manager.change(C.STATE_BELIEF)
        elif level == 4:
            self.manager.change(C.STATE_CARO)
        elif level == 5:
            self.manager.change(C.STATE_EIGHT_QUEENS)
        elif level == 6:
            self.manager.change(C.STATE_AND_OR)
        else:
            self.manager.change(C.STATE_GAMEPLAY)

    def _go_to_intro(self):
        self.manager.change(C.STATE_INTRO)

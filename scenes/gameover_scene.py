"""
scenes/gameover_scene.py
========================
Failure cutscene shown when energy reaches zero or Hill Climbing gets
stuck at a local maximum. It reuses the shared cutscene scaffold and
returns to the current gameplay level on SKIP/NEXT or R.
"""
import pygame

import pygame

import config as C
from scenes.cutscene_base import CutsceneScene
from systems.audio_manager import AudioManager
from ui.button import Button


class GameOverScene(CutsceneScene):
    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.back_button = Button(pygame.Rect(20, 20, 80, 28), "BACK", font_size=12,
                                  on_click=self._go_to_level_select)

    def on_enter(self, **kwargs):
        self.player.set_kit(self.game_state.kit_index)
        self.player.set_variant(self.player.variant_for_level(self.game_state.level))
        self.banner_text = "GAME OVER"
        self.graph = None

        self.badge_lines = [
            ("GAME OVER", 16, C.COL_GOLD_BRIGHT),
            ("Try Again", 14, C.COL_CREAM_TEXT),
        ]
        line = C.GAMEOVER_LINE_STUCK
        AudioManager.instance().play_sfx("game_over")

        self.dialogue.set_text(line, kit_index=self.game_state.kit_index)
        self._next_action = self._restart_level

    def handle_event(self, event):
        super().handle_event(event)
        self.back_button.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self._restart_level()

    def draw(self, surface):
        super().draw(surface)
        self.back_button.draw(surface)

    def _restart_level(self):
        self.game_state.restart_level()
        self.game_state.suggest_algorithm = None
        if self.game_state.level == 4:
            self.manager.change(C.STATE_CARO)
        elif self.game_state.level == 5:
            self.manager.change(C.STATE_EIGHT_QUEENS)
        else:
            self.manager.change(C.STATE_GAMEPLAY)

    def _go_to_level_select(self):
        self.manager.change(C.STATE_LEVEL_SELECT)

"""
scenes/intro_scene.py
=======================
Scene 1 from the design doc: opening cutscene introducing the game,
ending with the player in the Academy Green kit. SKIP/advance moves
straight into Level 0 gameplay.
"""
import pygame

import config as C
from scenes.cutscene_base import CutsceneScene
from systems.audio_manager import AudioManager
from ui.button import Button


class IntroScene(CutsceneScene):
    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.back_button = Button(pygame.Rect(20, 20, 80, 28), "BACK", font_size=12,
                                  on_click=self._go_to_level_select)

    def on_enter(self, **kwargs):
        self.player.set_kit(0)
        self.banner_text = None
        self.badge_lines = None
        self.graph = None
        self.dialogue.set_text(C.INTRO_LINE, kit_index=0)
        self._next_action = self._go_to_gameplay
        AudioManager.instance().play_bgm("main_menu")

    def _go_to_gameplay(self):
        self.manager.change(C.STATE_LEVEL_SELECT)

    def handle_event(self, event):
        super().handle_event(event)
        self.back_button.handle_event(event)

    def draw(self, surface):
        super().draw(surface)
        self.back_button.draw(surface)

    def _go_to_level_select(self):
        self.manager.change(C.STATE_LEVEL_SELECT)

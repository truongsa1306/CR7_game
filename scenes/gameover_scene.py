"""
scenes/gameover_scene.py
========================
Failure cutscene shown when energy reaches zero or Hill Climbing gets
stuck at a local maximum. It reuses the shared cutscene scaffold and
returns to the current gameplay level on SKIP/NEXT or R.
"""
import pygame

import config as C
from scenes.cutscene_base import CutsceneScene
from systems.audio_manager import AudioManager


class GameOverScene(CutsceneScene):
    def on_enter(self, **kwargs):
        self.player.set_kit(self.game_state.kit_index)
        self.banner_text = "GAME OVER"
        self.graph = None

        if self.game_state.gameover_reason == "stuck":
            self.badge_lines = [
                ("LOCAL MAXIMA", 15, C.COL_GOLD_BRIGHT),
                ("Try:", 12, C.COL_CREAM_TEXT),
                ("Stochastic HC", 14, C.COL_CREAM_TEXT),
            ]
            line = C.GAMEOVER_LINE_STUCK
            AudioManager.instance().play_sfx("local_maxima")
        else:
            self.badge_lines = [
                ("ENERGY: 0", 16, C.COL_GOLD_BRIGHT),
                ("Try Again", 14, C.COL_CREAM_TEXT),
            ]
            line = C.GAMEOVER_LINE_ENERGY
            AudioManager.instance().play_sfx("game_over")

        self.dialogue.set_text(line, kit_index=self.game_state.kit_index)
        self._next_action = self._restart_level

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self._restart_level()

    def _restart_level(self):
        self.game_state.restart_level()
        self.game_state.suggest_algorithm = None
        self.manager.change(C.STATE_GAMEPLAY)

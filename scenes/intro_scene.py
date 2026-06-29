"""
scenes/intro_scene.py
=======================
Scene 1 from the design doc: opening cutscene introducing the game,
ending with the player in the Academy Green kit. SKIP/advance moves
straight into Level 0 gameplay.
"""
import config as C
from scenes.cutscene_base import CutsceneScene
from systems.audio_manager import AudioManager


class IntroScene(CutsceneScene):
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

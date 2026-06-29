"""
scenes/victory_scene.py
=======================
Final celebration scene after CR7 reaches the World Cup on the last
level. It keeps the same ornate cutscene frame and adds fireworks.
"""
import random

import pygame

import config as C
from effects.particles import ParticleSystem
from scenes.cutscene_base import CutsceneScene
from systems.audio_manager import AudioManager
from ui.panel import draw_outer_frame, draw_stadium_background


class VictoryScene(CutsceneScene):
    def __init__(self, manager, game_state):
        super().__init__(manager, game_state)
        self.particles = ParticleSystem()
        self.elapsed = 0.0
        self._rng = random.Random(77)

    def on_enter(self, **kwargs):
        self.elapsed = 0.0
        self.particles.clear()
        self.player.set_kit(self.game_state.kit_index)
        self.banner_text = "WORLD CUP WON!"
        self.badge_lines = [
            ("FINAL", 16, C.COL_GOLD_BRIGHT),
            ("Energy Left:", 13, C.COL_CREAM_TEXT),
            (str(self.game_state.energy), 18, C.COL_GOLD_BRIGHT),
        ]
        self.graph = ("Champion Path", [1, 3, 5, 8, 13, 21, 34])
        self.dialogue.set_text(C.VICTORY_LINE, kit_index=self.game_state.kit_index)
        self._next_action = self._restart_campaign
        AudioManager.instance().play_sfx("siuuu")

    def update(self, dt):
        super().update(dt)
        self.elapsed += dt
        self.particles.update(dt)
        if int((self.elapsed - dt) * 2) != int(self.elapsed * 2):
            self.particles.emit_firework(
                (self._rng.randint(150, 880), self._rng.randint(70, 250)),
                count=34,
                speed=190,
                life=1.25,
            )
        self.particles.emit_confetti((80, C.SCREEN_W - 80), 20, count=3)

    def draw(self, surface):
        draw_stadium_background(surface)
        self.particles.draw(surface)
        self._draw_banner(surface, self.banner_text)
        center = C.CHIBI_PLAYER_RECT.center
        self.player.draw_at(surface, center)
        self._draw_badge(surface, self.badge_lines)
        self._draw_graph(surface, *self.graph)
        self.dialogue.draw(surface)
        draw_outer_frame(surface)

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self._restart_campaign()

    def _restart_campaign(self):
        self.game_state.level = 0
        self.game_state.kit_index = 0
        self.game_state.restart_level()
        self.manager.change(C.STATE_INTRO)

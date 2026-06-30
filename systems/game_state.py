"""
systems/game_state.py
=======================
Tiny mutable bag of state that persists across scene transitions:
current level, unlocked kit, and the reason for the last game-over
(so the GameOver scene can show the right message and the gameplay
scene can decide which algorithm to suggest on restart).
"""
import config as C


class GameState:
    def __init__(self):
        self.level = 0
        self.kit_index = 0
        self.gameover_reason = "stuck"   # "stuck" only, energy-based death removed
        self.suggest_algorithm = None      # e.g. "Stochastic HC" after a local-maxima death

    def advance_level(self):
        self.level = min(self.level + 1, max(C.LEVEL_NAMES.keys()))
        self.kit_index = self.level

    def restart_level(self):
        pass

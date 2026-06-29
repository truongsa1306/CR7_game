"""
systems/game_state.py
=======================
Tiny mutable bag of state that persists across scene transitions:
current level, energy, unlocked kit, and the reason for the last
game-over (so the GameOver scene can show the right message and the
gameplay scene can decide which algorithm to suggest on restart).
"""
import config as C


class GameState:
    def __init__(self):
        self.level = 0
        self.energy = C.START_ENERGY
        self.kit_index = 0
        self.gameover_reason = "energy"   # "energy" | "stuck"
        self.suggest_algorithm = None      # e.g. "Stochastic HC" after a local-maxima death

    def reset_energy(self):
        self.energy = C.START_ENERGY

    def spend_energy(self, amount):
        self.energy = max(0, self.energy - amount)

    def advance_level(self):
        self.level = min(self.level + 1, max(C.LEVEL_NAMES.keys()))
        self.kit_index = self.level
        self.reset_energy()

    def restart_level(self):
        self.reset_energy()

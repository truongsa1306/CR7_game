"""
scenes/base_scene.py
======================
Minimal interface every scene implements. Kept intentionally tiny --
this project favors plain composition over a heavyweight ECS.
"""


class BaseScene:
    def __init__(self, manager, game_state):
        self.manager = manager
        self.game_state = game_state

    def on_enter(self, **kwargs):
        """Called once when the scene manager switches to this scene."""

    def on_exit(self):
        """Called once right before switching away from this scene."""

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surface):
        pass

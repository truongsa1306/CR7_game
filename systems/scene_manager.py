"""
systems/scene_manager.py
==========================
The "vòng lặp State Machine chính" from the design doc: a thin
registry + switcher between scene instances. Scenes are constructed
once and reused (on_enter/on_exit reset their internal state), which
keeps transitions cheap and avoids reallocating UI widgets every time.
"""


class SceneManager:
    def __init__(self):
        self.scenes = {}
        self.current_key = None
        self.current_scene = None

    def register(self, key, scene):
        self.scenes[key] = scene

    def change(self, key, **kwargs):
        if self.current_scene is not None:
            self.current_scene.on_exit()
        self.current_key = key
        self.current_scene = self.scenes[key]
        self.current_scene.on_enter(**kwargs)

    def handle_event(self, event):
        if self.current_scene:
            self.current_scene.handle_event(event)

    def update(self, dt):
        if self.current_scene:
            self.current_scene.update(dt)

    def draw(self, surface):
        if self.current_scene:
            self.current_scene.draw(surface)

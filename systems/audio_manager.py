"""
systems/audio_manager.py
=========================
Thin wrapper around pygame.mixer that maps the asset-structure doc's
audio filenames to play calls. If mixer init fails (no sound device in
this environment) or a file is missing, every call becomes a safe no-op
instead of crashing the game.
"""
import pygame
import config as C

BGM_FILES = {
    "main_menu": "audio/bgm/main_menu.mp3",
    "gameplay_search": "audio/bgm/gameplay_search.mp3",
    "stadium_crowd_loop": "audio/bgm/stadium_crowd_loop.wav",
}

SFX_FILES = {
    "button_click": "audio/sfx/button_click.wav",
    "cell_step": "audio/sfx/cell_step.wav",
    "danger_trigger": "audio/sfx/danger_trigger.wav",
    "level_up": "audio/sfx/level_up.wav",
    "local_maxima": "audio/sfx/local_maxima.wav",
    "game_over": "audio/sfx/game_over.wav",
    "siuuu": "audio/sfx/siuuu.wav",
}


class AudioManager:
    _instance = None

    def __init__(self):
        self.enabled = False
        self._sfx_cache = {}
        self._current_bgm = None
        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error as e:
            print(f"[AudioManager] mixer unavailable, audio disabled: {e}")

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    def _load_sfx(self, name):
        if name in self._sfx_cache:
            return self._sfx_cache[name]
        rel = SFX_FILES.get(name)
        sound = None
        if rel:
            path = C.ASSETS_DIR / rel
            if path.exists():
                try:
                    sound = pygame.mixer.Sound(str(path))
                except pygame.error:
                    sound = None
        self._sfx_cache[name] = sound
        return sound

    def play_sfx(self, name, volume=1.0):
        if not self.enabled:
            return
        sound = self._load_sfx(name)
        if sound is not None:
            sound.set_volume(volume)
            sound.play()

    def play_bgm(self, name, loop=True, volume=0.5):
        if not self.enabled or name == self._current_bgm:
            return
        rel = BGM_FILES.get(name)
        if not rel:
            return
        path = C.ASSETS_DIR / rel
        if not path.exists():
            self._current_bgm = name  # still mark, avoid log spam every frame
            return
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1 if loop else 0)
            self._current_bgm = name
        except pygame.error:
            pass

    def stop_bgm(self):
        if self.enabled:
            pygame.mixer.music.stop()
        self._current_bgm = None

"""
entities/player.py
====================
The on-grid avatar (and the cutscene "chibi" stand-in use the same
sprite set). Handles smooth interpolated movement from cell to cell
plus a simple idle/walk animation timer so we get the "multi-frame
sprite sheet (idle, step, waving)" behaviour described in the asset
doc, even with procedural placeholder art.
"""
import pygame
import config as C
from systems.asset_manager import AssetManager, placeholder_chibi
from ui.animation import Tween, ease_out_cubic

CHIBI_SIZE = (50, 96)
MOVE_DURATION = 0.28  # seconds per cell hop


class Player:
    def __init__(self, kit_index=0):
        self.kit_index = kit_index
        self.col = 0
        self.row = 0
        self.pixel_pos = (0, 0)   # current rendered top-left, world space
        self._tween_x = None
        self._tween_y = None
        self.anim_time = 0.0
        self.state = "idle"      # idle | walk | wave

    def set_kit(self, kit_index):
        self.kit_index = kit_index

    def place_at_grid(self, col, row, origin, cell_size):
        self.col, self.row = col, row
        self.pixel_pos = self._cell_to_pixel(col, row, origin, cell_size)

    def _cell_to_pixel(self, col, row, origin, cell_size):
        x = origin[0] + col * cell_size + cell_size // 2 - CHIBI_SIZE[0] // 2
        y = origin[1] + row * cell_size + cell_size - CHIBI_SIZE[1] + 6
        return (x, y)

    def move_to_grid(self, col, row, origin, cell_size):
        target = self._cell_to_pixel(col, row, origin, cell_size)
        self._tween_x = Tween(self.pixel_pos[0], target[0], MOVE_DURATION, ease_out_cubic)
        self._tween_y = Tween(self.pixel_pos[1], target[1], MOVE_DURATION, ease_out_cubic)
        self.col, self.row = col, row
        self.state = "walk"

    @property
    def is_moving(self):
        return self._tween_x is not None and not self._tween_x.done

    def update(self, dt):
        self.anim_time += dt
        if self._tween_x is not None:
            x = self._tween_x.update(dt)
            y = self._tween_y.update(dt)
            self.pixel_pos = (x, y)
            if self._tween_x.done:
                self._tween_x = None
                self._tween_y = None
                self.state = "idle"

    def draw(self, surface):
        am = AssetManager.instance()
        kit_color = C.KITS[self.kit_index]["color"]
        kit_name = C.KITS[self.kit_index]["name"]
        sprite = am.get_image(
            f"sprites/characters/cr7_chibi_{kit_name}.png",
            size=CHIBI_SIZE,
            placeholder=lambda size: placeholder_chibi(size, kit_color),
        )
        # tiny vertical bob during walk to fake a step animation without
        # needing a real multi-frame sheet yet
        bob = 0
        if self.state == "walk":
            import math
            bob = int(2 * abs(math.sin(self.anim_time * 16)))
        x, y = self.pixel_pos
        surface.blit(sprite, (x, y - bob))

    def draw_at(self, surface, center_pos):
        """Used by cutscenes: draw centered at an arbitrary screen point."""
        am = AssetManager.instance()
        kit_color = C.KITS[self.kit_index]["color"]
        kit_name = C.KITS[self.kit_index]["name"]
        sprite = am.get_image(
            f"sprites/characters/cr7_chibi_{kit_name}.png",
            size=CHIBI_SIZE,
            placeholder=lambda size: placeholder_chibi(size, kit_color),
        )
        rect = sprite.get_rect(center=center_pos)
        surface.blit(sprite, rect.topleft)

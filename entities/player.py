"""
entities/player.py
====================
Shared CR7 avatar renderer used by grid levels, cutscenes and compact
algorithm visualisations.  The sprite source is the pixel sheet exported
into directional idle/walk frames; if those files are unavailable the
old procedural chibi placeholder still keeps the scene playable.
"""
import pygame
import config as C
from systems.asset_manager import AssetManager, placeholder_chibi
from ui.animation import Tween, ease_out_cubic

CHIBI_SIZE = (50, 96)
CUTSCENE_SIZE = (82, 156)
MOVE_DURATION = 0.28  # seconds per cell hop
STEP_FPS = 9.5
SIU_FPS = 7.0

IDLE_FRAMES = {
    "down": "sprites/characters/cr7_pixel_idle_down.png",
    "up": "sprites/characters/cr7_pixel_idle_up.png",
    "right": "sprites/characters/cr7_pixel_idle_right.png",
    "left": "sprites/characters/cr7_pixel_idle_left.png",
}

WALK_FRAMES = {
    "down": [
        "sprites/characters/cr7_pixel_walk_down_0.png",
        "sprites/characters/cr7_pixel_idle_down.png",
        "sprites/characters/cr7_pixel_walk_down_1.png",
        "sprites/characters/cr7_pixel_idle_down.png",
    ],
    "up": [
        "sprites/characters/cr7_pixel_walk_up_0.png",
        "sprites/characters/cr7_pixel_idle_up.png",
        "sprites/characters/cr7_pixel_walk_up_1.png",
        "sprites/characters/cr7_pixel_idle_up.png",
    ],
    "right": [
        "sprites/characters/cr7_pixel_walk_right_0.png",
        "sprites/characters/cr7_pixel_walk_right_1.png",
        "sprites/characters/cr7_pixel_walk_right_2.png",
        "sprites/characters/cr7_pixel_walk_right_1.png",
    ],
    "left": [
        "sprites/characters/cr7_pixel_walk_left_0.png",
        "sprites/characters/cr7_pixel_walk_left_1.png",
        "sprites/characters/cr7_pixel_walk_left_2.png",
        "sprites/characters/cr7_pixel_walk_left_1.png",
    ],
}

REAL_SHEET = "sprites/characters/cr7_real_spritesheet.png"
JUVE_SHEET = "sprites/characters/cr7_juve_spritesheet.png"

REAL_WALK_RECTS = [
    (28, 285, 100, 166),
    (143, 285, 100, 166),
    (257, 285, 100, 166),
    (372, 285, 99, 166),
    (487, 286, 98, 165),
    (601, 286, 99, 165),
]
REAL_SIU_RECTS = [
    (25, 740, 159, 161),
    (266, 783, 64, 156),
    (413, 770, 170, 166),
    (635, 760, 171, 168),
    (33, 980, 210, 212),
    (326, 981, 128, 186),
    (541, 981, 227, 205),
]

JUVE_IDLE_RECTS = [
    (20, 63, 113, 178),
    (168, 63, 116, 178),
    (317, 63, 114, 178),
    (466, 63, 116, 178),
]
JUVE_WALK_RECTS = [
    (19, 572, 107, 188),
    (149, 572, 107, 188),
    (283, 572, 105, 187),
    (411, 572, 106, 187),
    (545, 573, 105, 186),
    (679, 572, 107, 187),
]
JUVE_CELEBRATION_RECTS = [
    (19, 316, 112, 180),
    (168, 316, 116, 180),
    (317, 316, 115, 180),
    (466, 316, 115, 180),
]

ATLAS_VARIANTS = {
    "real": {
        "idle": [(REAL_SHEET, (410, 51, 70, 156))],
        "walk": [(REAL_SHEET, rect) for rect in REAL_WALK_RECTS],
        "siu": [(REAL_SHEET, rect) for rect in REAL_SIU_RECTS],
    },
    "juve": {
        "idle": [(JUVE_SHEET, rect) for rect in JUVE_IDLE_RECTS],
        "walk": [(JUVE_SHEET, rect) for rect in JUVE_WALK_RECTS],
        # The provided Juventus sheet has no dedicated SIU row; this uses its
        # own waving celebration instead of switching kits.
        "siu": [(JUVE_SHEET, rect) for rect in JUVE_CELEBRATION_RECTS],
    },
}


class Player:
    def __init__(self, kit_index=0):
        self.kit_index = kit_index
        self.col = 0
        self.row = 0
        self.pixel_pos = (0, 0)   # current rendered top-left, world space
        self._tween_x = None
        self._tween_y = None
        self.anim_time = 0.0
        self.state_time = 0.0
        self.state = "idle"      # idle | walk | wave
        self.facing = "down"
        self.sprite_variant = "default"

    def set_kit(self, kit_index):
        self.kit_index = kit_index

    def set_variant(self, variant):
        self.sprite_variant = variant if variant in ATLAS_VARIANTS else "default"

    @staticmethod
    def variant_for_level(level):
        if level == 1:
            return "real"
        if level == 2:
            return "juve"
        return "default"

    def set_state(self, state):
        if self.state != state:
            self.state = state
            self.state_time = 0.0

    def celebrate(self):
        self.facing = "down"
        self.set_state("siu")

    def place_at_grid(self, col, row, origin, cell_size):
        self.col, self.row = col, row
        self.pixel_pos = self._cell_to_pixel(col, row, origin, cell_size)
        self.set_state("idle")

    def _cell_to_pixel(self, col, row, origin, cell_size):
        x = origin[0] + col * cell_size + cell_size // 2 - CHIBI_SIZE[0] // 2
        y = origin[1] + row * cell_size + cell_size - CHIBI_SIZE[1] + 6
        return (x, y)

    def move_to_grid(self, col, row, origin, cell_size):
        self.facing = self.facing_from_delta(col - self.col, row - self.row)
        target = self._cell_to_pixel(col, row, origin, cell_size)
        self._tween_x = Tween(self.pixel_pos[0], target[0], MOVE_DURATION, ease_out_cubic)
        self._tween_y = Tween(self.pixel_pos[1], target[1], MOVE_DURATION, ease_out_cubic)
        self.col, self.row = col, row
        self.set_state("walk")

    @property
    def is_moving(self):
        return self._tween_x is not None and not self._tween_x.done

    def update(self, dt):
        self.anim_time += dt
        self.state_time += dt
        if self._tween_x is not None:
            x = self._tween_x.update(dt)
            y = self._tween_y.update(dt)
            self.pixel_pos = (x, y)
            if self._tween_x.done:
                self._tween_x = None
                self._tween_y = None
                self.set_state("idle")

    def draw(self, surface):
        draw_size = (86, 112) if self.state == "siu" else CHIBI_SIZE
        sprite = self.sprite_surface(
            kit_index=self.kit_index,
            state=self.state,
            facing=self.facing,
            anim_time=self.state_time,
            size=draw_size,
            variant=self.sprite_variant,
        )
        x, y = self.pixel_pos
        if self.state == "siu":
            base = (x + CHIBI_SIZE[0] // 2, y + CHIBI_SIZE[1])
            rect = sprite.get_rect(midbottom=base)
        else:
            rect = sprite.get_rect(topleft=(x, y))
        self._draw_shadow(surface, rect, strength=48)
        surface.blit(sprite, rect.topleft)

    def draw_at(self, surface, center_pos, size=CUTSCENE_SIZE, state="idle", facing="down", variant=None):
        """Used by cutscenes: draw centered at an arbitrary screen point."""
        sprite = self.sprite_surface(
            kit_index=self.kit_index,
            state=state,
            facing=facing,
            anim_time=self.anim_time,
            size=size,
            variant=self.sprite_variant if variant is None else variant,
        )
        rect = sprite.get_rect(center=center_pos)
        self._draw_shadow(surface, rect, strength=58)
        surface.blit(sprite, rect.topleft)

    @staticmethod
    def facing_from_delta(dx, dy, fallback="down"):
        if abs(dx) >= abs(dy) and dx != 0:
            return "right" if dx > 0 else "left"
        if dy != 0:
            return "down" if dy > 0 else "up"
        return fallback

    @classmethod
    def sprite_surface(cls, kit_index=0, state="idle", facing="down", anim_time=0.0, size=CHIBI_SIZE, variant="default"):
        """Return a transparent box with the current CR7 frame bottom-aligned."""
        frame = cls._load_frame(cls._frame_source(state, facing, anim_time, variant), kit_index)
        return cls._fit_frame(frame, size)

    @classmethod
    def draw_in_rect(
        cls,
        surface,
        rect,
        kit_index=0,
        state="idle",
        facing="down",
        anim_time=0.0,
        at_goal=False,
        variant="default",
    ):
        """Draw CR7 inside one board cell while preserving pixel proportions."""
        frame = cls._load_frame(cls._frame_source(state, facing, anim_time, variant), kit_index)
        max_w = max(16, int(rect.width * (0.72 if at_goal else 0.88)))
        max_h = max(20, int(rect.height * (0.88 if at_goal else 1.16)))
        sprite = cls._fit_frame(frame, (max_w, max_h))
        anchor_x = rect.right - max(3, rect.width // 8) if at_goal else rect.centerx
        anchor_y = rect.bottom - max(1, rect.height // 22)
        actor_rect = sprite.get_rect(midbottom=(anchor_x, anchor_y))
        cls._draw_shadow(surface, actor_rect, strength=44)
        surface.blit(sprite, actor_rect.topleft)

    @staticmethod
    def _kit_color(kit_index):
        kit = C.KITS.get(kit_index, C.KITS[0])
        return kit["color"]

    @staticmethod
    def _frame_source(state, facing, anim_time, variant="default"):
        if variant in ATLAS_VARIANTS:
            action = "siu" if state == "siu" else ("walk" if state == "walk" else "idle")
            frames = ATLAS_VARIANTS[variant][action]
            fps = SIU_FPS if action == "siu" else STEP_FPS
            if action == "siu":
                index = min(len(frames) - 1, int(anim_time * fps))
            else:
                index = int(anim_time * fps) % len(frames)
            return frames[index]

        if state == "siu":
            frames = ATLAS_VARIANTS["real"]["siu"]
            return frames[min(len(frames) - 1, int(anim_time * SIU_FPS))]

        facing = facing if facing in IDLE_FRAMES else "down"
        if state == "walk":
            frames = WALK_FRAMES[facing]
            return frames[int(anim_time * STEP_FPS) % len(frames)]
        return IDLE_FRAMES[facing]

    _atlas_cache = {}

    @staticmethod
    def _load_frame(rel_path, kit_index):
        if isinstance(rel_path, tuple):
            sheet_path, rect = rel_path
            cache_key = (sheet_path, rect)
            if cache_key not in Player._atlas_cache:
                sheet = AssetManager.instance().get_image(sheet_path)
                frame = sheet.subsurface(pygame.Rect(rect)).copy()
                Player._remove_sheet_background(frame)
                Player._atlas_cache[cache_key] = frame
            return Player._atlas_cache[cache_key]

        kit_color = Player._kit_color(kit_index)
        am = AssetManager.instance()
        return am.get_image(
            rel_path,
            placeholder=lambda _size: placeholder_chibi(CHIBI_SIZE, kit_color),
        )

    @staticmethod
    def _remove_sheet_background(surface):
        surface.lock()
        try:
            for y in range(surface.get_height()):
                for x in range(surface.get_width()):
                    r, g, b, a = surface.get_at((x, y))
                    grayish = abs(r - g) < 10 and abs(g - b) < 10 and 35 < r < 135
                    if a > 0 and grayish:
                        surface.set_at((x, y), (r, g, b, 0))
        finally:
            surface.unlock()

    @staticmethod
    def _fit_frame(frame, size):
        box_w, box_h = size
        scale = min(box_w / max(1, frame.get_width()), box_h / max(1, frame.get_height()))
        target_size = (
            max(1, int(frame.get_width() * scale)),
            max(1, int(frame.get_height() * scale)),
        )
        scaled = pygame.transform.scale(frame, target_size)
        boxed = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        boxed.blit(scaled, scaled.get_rect(midbottom=(box_w // 2, box_h)))
        return boxed

    @staticmethod
    def _draw_shadow(surface, rect, strength=42):
        shadow_h = max(3, rect.height // 18)
        shadow_w = max(12, int(rect.width * 0.62))
        shadow = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, strength), shadow.get_rect())
        surface.blit(shadow, shadow.get_rect(center=(rect.centerx, rect.bottom - shadow_h // 2)))

"""
systems/asset_manager.py
=========================
Centralised loader/cache for images and fonts.

Design goal: the game must run today, even though no real hand-drawn
sprite/font files exist on disk yet. Every getter therefore tries the
real asset path first; if the file is missing it synthesises a
reasonable pixel-art-style placeholder of the correct size so layout
and gameplay can be fully exercised. Drop real files into the paths
declared in the asset structure doc and they will be picked up
automatically -- no code changes required.
"""
import pygame
import config as C

TERRAIN_TILE_SIZE = 64
TERRAIN_TILE_NAMES = (
    "grass",
    "path",
    "stone",
    "danger",
    "fire_ground",
    "silver",
    "start",
    "goal",
)

PIXEL_FONT_CHARS = "0123456789+-=hgf.n"
PIXEL_GLYPH_W = 11
PIXEL_GLYPH_H = 15


class AssetManager:
    _instance = None

    def __init__(self):
        self._images = {}
        self._fonts = {}
        self._missing_warned = set()

    # ------------------------------------------------------------------
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    def _warn_once(self, path):
        if path not in self._missing_warned:
            self._missing_warned.add(path)
            print(f"[AssetManager] placeholder used for missing asset: {path}")

    # ------------------------------------------------------------------
    def get_image(self, rel_path, size=None, placeholder=None):
        """
        rel_path: path relative to assets/ (e.g. 'sprites/ui/gem_currency.png')
        size: optional (w, h) to scale to
        placeholder: optional callable(size) -> Surface used instead of the
                     generic placeholder if the file is missing
        """
        key = (rel_path, size)
        if key in self._images:
            return self._images[key]

        full_path = C.ASSETS_DIR / rel_path
        surf = None
        if full_path.exists():
            try:
                surf = pygame.image.load(str(full_path)).convert_alpha()
            except pygame.error:
                surf = None

        if surf is None:
            self._warn_once(rel_path)
            target_size = size or (64, 64)
            if placeholder is not None:
                surf = placeholder(target_size)
            else:
                surf = self._default_placeholder(target_size, rel_path)
        elif size is not None:
            surf = pygame.transform.smoothscale(surf, size)

        self._images[key] = surf
        return surf

    # ------------------------------------------------------------------
    def _default_placeholder(self, size, label_hint=""):
        """Magenta/black checker = classic 'missing texture' look,
        but pixel-arted and labeled for dev clarity."""
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        tile = 8
        for y in range(0, h, tile):
            for x in range(0, w, tile):
                even = ((x // tile) + (y // tile)) % 2 == 0
                color = (200, 40, 200, 255) if even else (20, 20, 20, 255)
                pygame.draw.rect(surf, color, (x, y, tile, tile))
        pygame.draw.rect(surf, C.COL_GOLD, surf.get_rect(), 2)
        return surf

    # ------------------------------------------------------------------
    def get_font(self, rel_path, size):
        key = (rel_path, size)
        if key in self._fonts:
            return self._fonts[key]

        full_path = C.ASSETS_DIR / rel_path
        font = None
        if full_path.exists():
            try:
                font = pygame.font.Font(str(full_path), size)
            except pygame.error:
                font = None

        if font is None:
            self._warn_once(rel_path)
            # Fallback: a monospace-ish system font keeps the pixel feel
            font = pygame.font.SysFont("couriernew,consolas,monospace", size, bold=True)

        self._fonts[key] = font
        return font

    # ------------------------------------------------------------------
    def font_primary(self, size):
        return self.get_font("fonts/pixel_primary.ttf", size)

    def font_bold(self, size):
        return self.get_font("fonts/pixel_bold.ttf", size)

    # ------------------------------------------------------------------
    def get_terrain_tile(self, tile_name, size=None):
        tile_name = tile_name if tile_name in TERRAIN_TILE_NAMES else "grass"
        key = ("terrain_tile", tile_name, size)
        if key in self._images:
            return self._images[key]

        sheet = self.get_image("sprites/environment/terrain_tiles.png")
        index = TERRAIN_TILE_NAMES.index(tile_name)
        rect = pygame.Rect(index * TERRAIN_TILE_SIZE, 0, TERRAIN_TILE_SIZE, TERRAIN_TILE_SIZE)
        if sheet.get_width() >= rect.right and sheet.get_height() >= rect.bottom:
            tile = sheet.subsurface(rect).copy()
        else:
            tile = self._default_placeholder((TERRAIN_TILE_SIZE, TERRAIN_TILE_SIZE), tile_name)
        if size is not None:
            tile = pygame.transform.scale(tile, size)
        self._images[key] = tile
        return tile

    def get_pixel_glyph(self, char, scale=2):
        if char == " ":
            return None
        char = char if char in PIXEL_FONT_CHARS else "0"
        scale = max(1, int(scale))
        key = ("pixel_glyph", char, scale)
        if key in self._images:
            return self._images[key]

        sheet = self.get_image("sprites/ui/pixel_numbers.png")
        index = PIXEL_FONT_CHARS.index(char)
        rect = pygame.Rect(index * PIXEL_GLYPH_W, 0, PIXEL_GLYPH_W, PIXEL_GLYPH_H)
        if sheet.get_width() >= rect.right and sheet.get_height() >= rect.bottom:
            glyph = sheet.subsurface(rect).copy()
        else:
            glyph = self._default_placeholder((PIXEL_GLYPH_W, PIXEL_GLYPH_H), char)
        if scale != 1:
            glyph = pygame.transform.scale(glyph, (glyph.get_width() * scale, glyph.get_height() * scale))
        self._images[key] = glyph
        return glyph


def terrain_tile_name(kind, value=None):
    if kind == "wall":
        return "stone"
    if kind == "fire" or (value is not None and value <= -10):
        return "fire_ground"
    if kind == "danger" or (value is not None and value < 0):
        return "danger"
    if kind == "start":
        return "start"
    if kind == "trophy":
        return "goal"
    if value == 0 or kind == "path":
        return "path"
    if kind == "grass" or (value is not None and value > 0):
        return "grass"
    return "silver"


def draw_pixel_number(surface, text, pos, scale=2, align="center", spacing=1):
    am = AssetManager.instance()
    glyphs = []
    width = 0
    height = 0
    for raw_char in str(text):
        glyph = am.get_pixel_glyph(raw_char, scale)
        glyphs.append(glyph)
        if glyph is None:
            width += PIXEL_GLYPH_W * scale // 2
            height = max(height, PIXEL_GLYPH_H * scale)
        else:
            width += glyph.get_width()
            height = max(height, glyph.get_height())
        width += spacing * scale
    if glyphs:
        width -= spacing * scale

    if align == "center":
        x = int(pos[0] - width / 2)
        y = int(pos[1] - height / 2)
    else:
        x = int(pos[0])
        y = int(pos[1])

    cursor = x
    for glyph in glyphs:
        if glyph is None:
            cursor += PIXEL_GLYPH_W * scale // 2 + spacing * scale
            continue
        surface.blit(glyph, (cursor, y))
        cursor += glyph.get_width() + spacing * scale
    return pygame.Rect(x, y, width, height)


# ---------------------------------------------------------------------------
# Procedural placeholder factories for specific sprite categories.
# These produce something visually *appropriate* (not just a checker)
# so the game looks reasonable before real art lands.
# ---------------------------------------------------------------------------

def placeholder_portrait(size, kit_color):
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (52, 34, 28), surf.get_rect(), border_radius=6)
    face = pygame.Rect(int(w * 0.18), int(h * 0.16), int(w * 0.64), int(h * 0.58))
    pygame.draw.rect(surf, (224, 184, 148), face, border_radius=10)
    pygame.draw.rect(surf, (34, 24, 20), (face.left, face.top, face.width, int(face.height * 0.28)), border_radius=8)
    eye_y = face.top + int(face.height * 0.46)
    pygame.draw.rect(surf, (24, 18, 16), (face.left + int(face.width * 0.24), eye_y, 9, 3))
    pygame.draw.rect(surf, (24, 18, 16), (face.right - int(face.width * 0.24) - 9, eye_y, 9, 3))
    pygame.draw.rect(surf, kit_color, (int(w * 0.04), int(h * 0.72), int(w * 0.92), int(h * 0.28)), border_radius=6)
    pygame.draw.rect(surf, C.COL_GOLD, surf.get_rect(), 3, border_radius=6)
    return surf


def placeholder_chibi(size, kit_color):
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    head_r = int(w * 0.42)
    cx = w // 2
    pygame.draw.circle(surf, (224, 196, 168), (cx, head_r), head_r)
    body_rect = pygame.Rect(int(w * 0.18), int(head_r * 1.5), int(w * 0.64), int(h * 0.42))
    pygame.draw.rect(surf, kit_color, body_rect, border_radius=4)
    if C.KITS.get(3, {}).get("color") == kit_color:
        stripe_w = max(2, body_rect.width // 5)
        for x in range(body_rect.left, body_rect.right, stripe_w * 2):
            pygame.draw.rect(surf, (235, 235, 235), (x, body_rect.top, stripe_w, body_rect.height))
    leg_w = int(body_rect.width * 0.35)
    leg_top = body_rect.bottom
    pygame.draw.rect(surf, (40, 40, 40), (body_rect.left, leg_top, leg_w, h - leg_top), border_radius=2)
    pygame.draw.rect(surf, (40, 40, 40), (body_rect.right - leg_w, leg_top, leg_w, h - leg_top), border_radius=2)
    return surf


def placeholder_trophy(size):
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    gold = C.COL_GOLD_BRIGHT
    cup = pygame.Rect(int(w * 0.25), int(h * 0.15), int(w * 0.5), int(h * 0.45))
    pygame.draw.rect(surf, gold, cup, border_radius=6)
    pygame.draw.rect(surf, C.COL_GOLD, cup, 2, border_radius=6)
    pygame.draw.polygon(surf, gold, [
        (cup.left, cup.top), (int(cup.left - w * 0.12), int(cup.top + h * 0.1)),
        (int(cup.left - w * 0.12), int(cup.top + h * 0.25)), (cup.left, int(cup.top + h * 0.2)),
    ])
    pygame.draw.polygon(surf, gold, [
        (cup.right, cup.top), (int(cup.right + w * 0.12), int(cup.top + h * 0.1)),
        (int(cup.right + w * 0.12), int(cup.top + h * 0.25)), (cup.right, int(cup.top + h * 0.2)),
    ])
    pygame.draw.rect(surf, gold, pygame.Rect(int(w * 0.42), cup.bottom, int(w * 0.16), int(h * 0.18)))
    pygame.draw.rect(surf, gold, pygame.Rect(int(w * 0.28), int(h * 0.85), int(w * 0.44), int(h * 0.08)), border_radius=2)
    return surf

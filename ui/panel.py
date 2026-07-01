"""
ui/panel.py
===========
9-slice panel rendering for the ornate wooden frame look used by the
outer screen border, the dialogue box, side panels, and badges.

If a real 'frame_border_tiles.png' / 'dialog_box_base.png' is dropped
into assets/sprites/ui/, it is sliced and used. Otherwise a procedural
wood-grain + gold-corner panel is drawn, which gives the same visual
language (dark wood fill, lighter bevel, gold ornate corners) without
needing real art.
"""
import pygame
import config as C
from systems.asset_manager import AssetManager

UI_SPRITE_SIZE = 64
BACKGROUND_FRAME_SIZE = (1024, 576)


def _asset_exists(rel_path):
    return (C.ASSETS_DIR / rel_path).exists()


def _tile_surface(surface, tile, rect):
    if rect.width <= 0 or rect.height <= 0:
        return
    clip_before = surface.get_clip()
    surface.set_clip(rect)
    for y in range(rect.top, rect.bottom, tile.get_height()):
        for x in range(rect.left, rect.right, tile.get_width()):
            surface.blit(tile, (x, y))
    surface.set_clip(clip_before)


def _ui_sprite(sheet, col, row, size=UI_SPRITE_SIZE):
    return sheet.subsurface(pygame.Rect(col * size, row * size, size, size)).copy()


def draw_wood_panel(surface, rect, border=8, corner=14, fill=None, border_color=None,
                     accent_color=None, radius=4):
    """Procedural 9-slice-style wooden panel: flat fill + beveled border +
    gold corner accents. Cheap to draw every frame, looks consistent with
    the ornate-frame aesthetic in the screenshots."""
    if _draw_sprite_panel(surface, rect, border, corner, fill, border_color, accent_color, radius):
        return

    fill = fill or C.COL_WOOD_MED
    border_color = border_color or C.COL_WOOD_DARK
    accent_color = accent_color or C.COL_GOLD

    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border_color, rect, border, border_radius=radius)

    # inner highlight bevel
    inner = rect.inflate(-border * 2, -border * 2)
    if inner.width > 0 and inner.height > 0:
        pygame.draw.rect(surface, C.COL_WOOD_LIGHT, inner, 2, border_radius=max(radius - 2, 0))

    # gold corner ornaments
    _corner_ornament(surface, (rect.left, rect.top), corner, accent_color, (1, 1))
    _corner_ornament(surface, (rect.right, rect.top), corner, accent_color, (-1, 1))
    _corner_ornament(surface, (rect.left, rect.bottom), corner, accent_color, (1, -1))
    _corner_ornament(surface, (rect.right, rect.bottom), corner, accent_color, (-1, -1))


def _draw_sprite_panel(surface, rect, border, corner, fill, border_color, accent_color, radius):
    rel_path = "sprites/ui/dialog_frame_sheet.png"
    if not _asset_exists(rel_path):
        return False
    sheet = AssetManager.instance().get_image(rel_path)
    if sheet.get_width() < UI_SPRITE_SIZE * 4 or sheet.get_height() < UI_SPRITE_SIZE * 2:
        return False

    fill_tile = _ui_sprite(sheet, 0, 0)
    edge_tile = _ui_sprite(sheet, 1, 0)
    dark_tile = _ui_sprite(sheet, 2, 0)
    corner_sprites = (
        _ui_sprite(sheet, 0, 1),
        _ui_sprite(sheet, 1, 1),
        _ui_sprite(sheet, 2, 1),
        _ui_sprite(sheet, 3, 1),
    )

    pygame.draw.rect(surface, (40, 24, 17), rect, border_radius=radius)
    inner = rect.inflate(-border * 2, -border * 2)
    _tile_surface(surface, dark_tile, rect)
    if inner.width > 0 and inner.height > 0:
        _tile_surface(surface, fill_tile, inner)
        if fill is not None:
            tint = pygame.Surface(inner.size, pygame.SRCALPHA)
            tint.fill((*fill, 58))
            surface.blit(tint, inner.topleft)

    bars = (
        pygame.Rect(rect.left, rect.top, rect.width, border),
        pygame.Rect(rect.left, rect.bottom - border, rect.width, border),
        pygame.Rect(rect.left, rect.top, border, rect.height),
        pygame.Rect(rect.right - border, rect.top, border, rect.height),
    )
    for bar in bars:
        _tile_surface(surface, edge_tile, bar)

    line_color = border_color or C.COL_WOOD_DARK
    accent = accent_color or C.COL_GOLD
    pygame.draw.rect(surface, line_color, rect, max(1, border // 3), border_radius=radius)
    if inner.width > 0 and inner.height > 0:
        pygame.draw.rect(surface, (198, 137, 74), inner, 2, border_radius=max(radius - 2, 0))
        pygame.draw.rect(surface, (30, 18, 12), inner.inflate(4, 4), 1, border_radius=max(radius - 1, 0))

    ornament = min(max(24, corner * 3), max(24, rect.width // 3), max(24, rect.height // 2))
    positions = (
        (rect.left, rect.top),
        (rect.right - ornament, rect.top),
        (rect.left, rect.bottom - ornament),
        (rect.right - ornament, rect.bottom - ornament),
    )
    for sprite, pos in zip(corner_sprites, positions):
        scaled = pygame.transform.scale(sprite, (ornament, ornament))
        surface.blit(scaled, pos)
    pygame.draw.rect(surface, accent, rect.inflate(-3, -3), 1, border_radius=radius)
    return True


def _corner_ornament(surface, pos, size, color, direction):
    x, y = pos
    dx, dy = direction
    pts = [
        (int(x), int(y)),
        (int(x + dx * size), int(y)),
        (int(x + dx * size * 0.4), int(y + dy * size * 0.25)),
        (int(x + dx * size * 0.25), int(y + dy * size * 0.4)),
        (int(x), int(y + dy * size)),
    ]
    pygame.draw.polygon(surface, color, pts, width=0)
    pygame.draw.circle(surface, color, (int(x + dx * 4), int(y + dy * 4)), 3)


def draw_outer_frame(surface):
    """The main 1024x576 wooden screen border.

    Unlike draw_wood_panel(), this must never fill the full screen. It is
    drawn after the scene content, so only the border ring is painted.
    """
    rect = C.OUTER_FRAME_RECT
    border = C.OUTER_FRAME_BORDER
    inner = rect.inflate(-border * 2, -border * 2)

    bars = (
        pygame.Rect(rect.left, rect.top, rect.width, border),
        pygame.Rect(rect.left, rect.bottom - border, rect.width, border),
        pygame.Rect(rect.left, rect.top, border, rect.height),
        pygame.Rect(rect.right - border, rect.top, border, rect.height),
    )
    if _asset_exists("sprites/ui/dialog_frame_sheet.png"):
        sheet = AssetManager.instance().get_image("sprites/ui/dialog_frame_sheet.png")
        edge_tile = _ui_sprite(sheet, 1, 0)
        for bar in bars:
            _tile_surface(surface, edge_tile, bar)
            pygame.draw.rect(surface, C.COL_WOOD_DARK, bar, 2)
    else:
        for bar in bars:
            pygame.draw.rect(surface, C.COL_WOOD_MED, bar)
            pygame.draw.rect(surface, C.COL_WOOD_DARK, bar, 2)

    pygame.draw.rect(surface, C.COL_GOLD, rect.inflate(-6, -6), 2)
    pygame.draw.rect(surface, C.COL_GOLD, inner.inflate(4, 4), 2)

    _corner_ornament(surface, (rect.left + border, rect.top + border), 26, C.COL_GOLD, (1, 1))
    _corner_ornament(surface, (rect.right - border, rect.top + border), 26, C.COL_GOLD, (-1, 1))
    _corner_ornament(surface, (rect.left + border, rect.bottom - border), 26, C.COL_GOLD, (1, -1))
    _corner_ornament(surface, (rect.right - border, rect.bottom - border), 26, C.COL_GOLD, (-1, -1))


def draw_floodlights(surface):
    """Two floodlight glows top-left / top-right, matching the stadium look."""
    glow = pygame.Surface((220, 220), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 244, 200, 70), (110, 110), 110)
    pygame.draw.circle(glow, (255, 244, 200, 110), (110, 110), 60)
    for x in (40, C.SCREEN_W - 40 if hasattr(C, "SCREEN_W") else C.SCREEN_W - 40):
        surface.blit(glow, (x - 110, -60), special_flags=pygame.BLEND_RGBA_ADD)


def draw_stadium_background(surface):
    """Stadium interior backdrop: pitch-green floor + raked dark stands."""
    rel_path = "sprites/ui/stadium_background_sheet.png"
    if _asset_exists(rel_path):
        sheet = AssetManager.instance().get_image(rel_path)
        frame_w, frame_h = BACKGROUND_FRAME_SIZE
        frame_count = max(1, sheet.get_width() // frame_w)
        frame_index = (pygame.time.get_ticks() // 850) % frame_count
        frame = sheet.subsurface(pygame.Rect(frame_index * frame_w, 0, frame_w, frame_h)).copy()
        if frame.get_size() != surface.get_size():
            frame = pygame.transform.scale(frame, surface.get_size())
        surface.blit(frame, (0, 0))
        return

    surface.fill((26, 18, 14))
    # raked stands (simple repeating trapezoid bands, top half)
    stand_h = int(C.SCREEN_H * 0.34)
    bands = 9
    for i in range(bands):
        shade = 50 + i * 4
        y0 = int(i * stand_h / bands)
        pygame.draw.rect(surface, (shade, shade - 8, shade - 16),
                          (0, y0, C.SCREEN_W, stand_h // bands + 1))
    # pitch
    pitch_rect = pygame.Rect(0, stand_h, C.SCREEN_W, C.SCREEN_H - stand_h)
    pygame.draw.rect(surface, C.COL_GRASS_DARK, pitch_rect)
    stripe_w = 64
    for i, x in enumerate(range(0, C.SCREEN_W, stripe_w)):
        if i % 2 == 0:
            pygame.draw.rect(surface, C.COL_GRASS_LIGHT, (x, stand_h, stripe_w, pitch_rect.height))
    pygame.draw.line(surface, C.COL_WHITE, (0, stand_h + 14), (C.SCREEN_W, stand_h + 14), 2)
    draw_floodlights(surface)

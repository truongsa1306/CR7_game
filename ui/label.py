"""
ui/label.py
===========
Consistent text rendering helper: pixel font + drop shadow (the classic
"pixel game UI" look used for titles, stat numbers, and dialogue).
"""
import pygame
import config as C
from systems.asset_manager import AssetManager


def draw_text(surface, text, pos, size=20, color=None, bold=True, shadow=True,
              align="left", max_width=None):
    """
    pos: (x, y) -- meaning depends on `align`:
        'left'   -> top-left
        'center' -> top-center
        'right'  -> top-right
    """
    color = color or C.COL_CREAM_TEXT
    am = AssetManager.instance()
    font = am.font_bold(size) if bold else am.font_primary(size)

    lines = _wrap_text(font, text, max_width) if max_width else [text]
    x, y = pos
    line_h = font.get_linesize()
    for i, line in enumerate(lines):
        surf = font.render(line, True, color)
        rect = surf.get_rect()
        if align == "center":
            rect.midtop = (x, y + i * line_h)
        elif align == "right":
            rect.topright = (x, y + i * line_h)
        else:
            rect.topleft = (x, y + i * line_h)

        if shadow:
            shadow_surf = font.render(line, True, C.COL_BLACK)
            surface.blit(shadow_surf, (rect.x + 2, rect.y + 2))
        surface.blit(surf, rect)
    return line_h * len(lines)


def _wrap_text(font, text, max_width):
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = (cur + " " + word).strip()
        if font.size(trial)[0] <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_size(text, size=20, bold=True):
    am = AssetManager.instance()
    font = am.font_bold(size) if bold else am.font_primary(size)
    return font.size(text)

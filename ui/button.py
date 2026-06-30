"""
ui/button.py
============
Clickable wood-slice button (used for SKIP, algorithm select, Step/Auto
controls, and the Game Over restart prompt).
"""
import pygame
import config as C
from ui.label import draw_text, text_size
from systems.audio_manager import AudioManager


class Button:
    def __init__(self, rect, text, on_click=None, font_size=16, enabled=True):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.font_size = font_size
        self.hovered = False
        self.pressed = False
        self.enabled = enabled

    def handle_event(self, event):
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.rect.collidepoint(event.pos):
                AudioManager.instance().play_sfx("button_click")
                self.pressed = False
                try:
                    if self.on_click:
                        self.on_click()
                except Exception as exc:
                    import traceback
                    print(f"[Button] click failed for '{self.text}': {exc}")
                    traceback.print_exc()
                return True
            self.pressed = False
        return False

    def draw(self, surface):
        if not self.enabled:
            base, border = (40, 34, 28), (24, 18, 14)
            text_col = (120, 112, 100)
        elif self.pressed:
            base, border = (56, 36, 22), C.COL_GOLD
            text_col = C.COL_GOLD_BRIGHT
        elif self.hovered:
            base, border = (96, 62, 36), C.COL_GOLD
            text_col = C.COL_CREAM_TEXT
        else:
            base, border = (74, 46, 30), C.COL_WOOD_DARK
            text_col = C.COL_CREAM_TEXT

        pygame.draw.rect(surface, base, self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=6)

        tw, th = text_size(self.text, self.font_size)
        draw_text(surface, self.text,
                  (self.rect.centerx, self.rect.centery - th // 2),
                  size=self.font_size, color=text_col, align="center", shadow=False)


class ToggleGroup:
    """A row of mutually-exclusive buttons (e.g. algorithm picker)."""

    def __init__(self, rect, labels, on_select=None, font_size=14):
        self.buttons = []
        self.selected = 0
        n = len(labels)
        h = rect.height
        gap = 6
        w = (rect.width - gap * (n - 1)) / n
        for i, label in enumerate(labels):
            r = pygame.Rect(int(rect.x + i * (w + gap)), rect.y, int(w), h)
            self.buttons.append(Button(r, label, font_size=font_size,
                                        on_click=lambda i=i: self._select(i)))
        self.on_select = on_select

    def _select(self, i):
        self.selected = i
        if self.on_select:
            self.on_select(i)

    def handle_event(self, event):
        for btn in self.buttons:
            btn.handle_event(event)

    def draw(self, surface):
        for i, btn in enumerate(self.buttons):
            is_selected = i == self.selected
            btn.hovered = btn.hovered or is_selected
            border = C.COL_GOLD if is_selected else C.COL_WOOD_DARK
            base = (120, 80, 40) if is_selected else (74, 46, 30)
            text_color = C.COL_GOLD_BRIGHT if is_selected else C.COL_CREAM_TEXT
            pygame.draw.rect(surface, base, btn.rect, border_radius=6)
            pygame.draw.rect(surface, border, btn.rect, 2, border_radius=6)
            tw, th = text_size(btn.text, btn.font_size)
            draw_text(surface, btn.text,
                      (btn.rect.centerx, btn.rect.centery - th // 2),
                      size=btn.font_size, color=text_color, align="center", shadow=False)

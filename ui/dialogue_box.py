"""
ui/dialogue_box.py
===================
The bottom dialogue UI shared by every scene: wooden panel, character
portrait poking up over the top edge, typewriter text area, currency
icon, winged logo, and a SKIP button. Exact rects come from config.py
(BOTTOM DIALOGUE UI section of the UI spec).
"""
import pygame
import config as C
from ui.panel import draw_wood_panel
from ui.label import draw_text
from ui.button import Button
from systems.asset_manager import AssetManager, placeholder_portrait
from systems.audio_manager import AudioManager


class DialogueBox:
    def __init__(self, on_skip=None):
        self.text = ""
        self.shown_chars = 0.0
        self.kit_index = 0
        self.status_text = ""
        self.skip_btn = Button(C.SKIP_BUTTON_RECT, "SKIP", font_size=14,
                                on_click=self._handle_skip)
        self.on_skip = on_skip
        self._gem_phase = 0.0

    def set_text(self, text, kit_index=0):
        self.text = text
        self.shown_chars = 0.0
        self.kit_index = kit_index
        self.status_text = ""

    def set_status(self, status):
        self.status_text = status or ""

    def _handle_skip(self):
        # Skip finishes the typewriter instantly on first press,
        # advances the scene on second press.
        if self.shown_chars < len(self.text):
            self.shown_chars = len(self.text)
        elif callable(self.on_skip):
            try:
                self.on_skip()
            except Exception as exc:
                print(f"Skip handler failed: {exc}")

    @property
    def fully_revealed(self):
        return self.shown_chars >= len(self.text)

    def handle_event(self, event):
        self.skip_btn.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
            self._handle_skip()

    def update(self, dt):
        if self.shown_chars < len(self.text):
            self.shown_chars += C.TYPEWRITER_CPS * dt
        self._gem_phase += dt

    def draw(self, surface):
        panel_rect = C.DIALOG_PANEL_RECT
        draw_wood_panel(surface, panel_rect, border=6, corner=12)

        # Large portrait attached to the bottom dialogue frame.
        am = AssetManager.instance()
        kit_color = C.KITS[self.kit_index]["color"]
        portrait_rect = pygame.Rect(
            panel_rect.left + 42,
            panel_rect.top - 72,
            150,
            164,
        )
        plate_rect = portrait_rect.inflate(12, 10)
        pygame.draw.rect(surface, (34, 20, 15), plate_rect, border_radius=9)
        pygame.draw.rect(surface, (226, 184, 96), plate_rect, 3, border_radius=9)
        portrait = am.get_image(
            f"sprites/characters/cr7_portrait_{C.KITS[self.kit_index]['name']}.png",
            size=(portrait_rect.width, portrait_rect.height),
            placeholder=lambda size: placeholder_portrait(size, kit_color),
        )
        surface.blit(portrait, portrait_rect.topleft)
        pygame.draw.rect(surface, C.COL_GOLD, portrait_rect, 3, border_radius=8)

        # Typewriter text
        text_rect = pygame.Rect(
            portrait_rect.right + 24,
            panel_rect.top + 13,
            C.SKIP_BUTTON_RECT.left - portrait_rect.right - 38,
            panel_rect.height - 22,
        )
        visible = self.text[: int(self.shown_chars)]
        draw_text(surface, visible, text_rect.topleft, size=16,
                  color=C.COL_CREAM_TEXT, max_width=text_rect.width)

        if self.status_text:
            status_pos = (text_rect.left, text_rect.bottom - 18)
            draw_text(surface, self.status_text, status_pos, size=14,
                      color=C.COL_HIGHLIGHT_PURPLE, align="left", max_width=text_rect.width)

        # Currency / gem icon (simple pulsing emerald placeholder)
        import math
        gem_rect = C.CURRENCY_ICON_RECT
        gem_path = C.ASSETS_DIR / "sprites/ui/gem_currency.png"
        if gem_path.exists():
            gem = am.get_image("sprites/ui/gem_currency.png", size=(gem_rect.width, gem_rect.height))
            surface.blit(gem, gem_rect.topleft)
        else:
            pulse = 0.5 + 0.5 * math.sin(self._gem_phase * 3)
            gem_color = (40 + int(60 * pulse), 200, 120)
            pygame.draw.polygon(surface, gem_color, [
                (gem_rect.centerx, gem_rect.top),
                (gem_rect.right, gem_rect.centery),
                (gem_rect.centerx, gem_rect.bottom),
                (gem_rect.left, gem_rect.centery),
            ])
            pygame.draw.polygon(surface, C.COL_GOLD, [
                (gem_rect.centerx, gem_rect.top),
                (gem_rect.right, gem_rect.centery),
                (gem_rect.centerx, gem_rect.bottom),
                (gem_rect.left, gem_rect.centery),
            ], 2)

        # Winged logo.
        logo_rect = C.LOGO_RECT
        logo_path = C.ASSETS_DIR / "sprites/ui/cr7_winged_logo.png"
        if logo_path.exists():
            logo = am.get_image("sprites/ui/cr7_winged_logo.png", size=(logo_rect.width, logo_rect.height))
            surface.blit(logo, logo_rect.topleft)
        else:
            draw_text(surface, C.PLAYER_TAG, (logo_rect.centerx, logo_rect.top + 6),
                      size=20, color=C.COL_GOLD_BRIGHT, align="center")
            wing_y = logo_rect.centery + 10
            pygame.draw.line(surface, C.COL_GOLD, (logo_rect.left, wing_y),
                              (logo_rect.centerx - 14, wing_y - 6), 3)
            pygame.draw.line(surface, C.COL_GOLD, (logo_rect.right, wing_y),
                              (logo_rect.centerx + 14, wing_y - 6), 3)

        # Skip button -- visually hint "next" once text is fully revealed
        self.skip_btn.text = "NEXT" if self.fully_revealed else "SKIP"
        self.skip_btn.draw(surface)

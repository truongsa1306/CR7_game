import pygame

from systems.asset_manager import AssetManager

FIRE_FRAME_SIZE = 64
FIRE_FRAME_COUNT = 6


class FireAnimator:
    def __init__(self):
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def draw(self, surface, rect):
        sheet = AssetManager.instance().get_image("sprites/environment/fire_sheet.png")
        frame_count = max(1, min(FIRE_FRAME_COUNT, sheet.get_width() // FIRE_FRAME_SIZE))
        frame_index = int(self.t * 10 + rect.x * 0.03 + rect.y * 0.02) % frame_count
        frame_rect = pygame.Rect(frame_index * FIRE_FRAME_SIZE, 0, FIRE_FRAME_SIZE, FIRE_FRAME_SIZE)
        flame = sheet.subsurface(frame_rect).copy()
        flame = pygame.transform.scale(flame, rect.size)
        surface.blit(flame, rect.topleft)

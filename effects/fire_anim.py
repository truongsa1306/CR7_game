"""
effects/fire_anim.py
======================
Cheap animated fire flicker drawn on top of "fire" cells (-20 cost).
Mirrors the 4-frame fire_sheet.png described in the asset doc, but
drawn procedurally (layered flickering triangles) so it works without
the real sprite sheet.
"""
import math
import random
import pygame


class FireAnimator:
    def __init__(self):
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def draw(self, surface, rect):
        cx, cy = rect.centerx, rect.bottom - 6
        flicker = 0.5 + 0.5 * math.sin(self.t * 10 + rect.x * 0.3)
        base_h = rect.height * 0.55
        for i, (color, scale) in enumerate([
            ((90, 30, 10), 1.0), ((220, 90, 20), 0.75), ((255, 200, 60), 0.45)
        ]):
            h = base_h * scale * (0.8 + 0.2 * flicker)
            w = rect.width * 0.5 * scale
            sway = math.sin(self.t * 6 + i) * 3
            points = [
                (int(cx + sway), int(cy - h)),
                (int(cx - w / 2), int(cy)),
                (int(cx + w / 2), int(cy)),
            ]
            pygame.draw.polygon(surface, color, points)

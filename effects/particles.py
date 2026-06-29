"""
effects/particles.py
======================
Small generic particle system reused for:
- level-up gold sparkles around the player
- victory-scene fireworks / confetti
- danger/fire cell impact bursts
"""
import random
import math
import pygame


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "gravity")

    def __init__(self, x, y, vx, vy, life, color, size, gravity=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity

    def update(self, dt):
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0

    @property
    def alpha(self):
        return max(0, min(255, int(255 * (self.life / self.max_life))))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def clear(self):
        self.particles = []

    def emit_sparkle_burst(self, pos, count=24, colors=None, speed=140, life=0.9):
        colors = colors or [(255, 220, 140), (255, 245, 200), (227, 181, 95)]
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            spd = random.uniform(speed * 0.3, speed)
            vx, vy = math.cos(angle) * spd, math.sin(angle) * spd
            self.particles.append(Particle(
                pos[0], pos[1], vx, vy, random.uniform(life * 0.6, life),
                random.choice(colors), random.uniform(2, 4), gravity=60,
            ))

    def emit_firework(self, pos, count=40, color=None, speed=220, life=1.2):
        color = color or random.choice([
            (255, 90, 90), (90, 200, 255), (255, 220, 90), (140, 255, 140), (220, 140, 255)
        ])
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            spd = random.uniform(speed * 0.2, speed)
            vx, vy = math.cos(angle) * spd, math.sin(angle) * spd
            self.particles.append(Particle(
                pos[0], pos[1], vx, vy, random.uniform(life * 0.7, life),
                color, random.uniform(2, 3), gravity=140,
            ))

    def emit_confetti(self, x_range, y, count=6, colors=None):
        colors = colors or [(255, 90, 90), (90, 200, 255), (255, 220, 90), (140, 255, 140)]
        for _ in range(count):
            x = random.uniform(*x_range)
            self.particles.append(Particle(
                x, y, random.uniform(-30, 30), random.uniform(20, 60),
                random.uniform(2.0, 3.5), random.choice(colors),
                random.uniform(3, 5), gravity=80,
            ))

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surface):
        for p in self.particles:
            radius = max(1, int(p.size))
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p.color, p.alpha), (radius, radius), radius)
            surface.blit(s, (p.x - radius, p.y - radius))

"""
ui/animation.py
================
Small dependency-free tweening helpers. No external animation library
needed for a project this size -- a handful of easing functions plus a
Tween object covers banners, glows, badge pop-ins, etc.
"""
import math


def ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_in_out_sine(t):
    return -(math.cos(math.pi * t) - 1) / 2


def pulse(t, speed=1.0):
    """Returns a smooth 0..1..0 pulse, useful for glow/sparkle effects."""
    return (math.sin(t * speed * math.pi * 2) + 1) / 2


class Tween:
    """A single value animated from `start` to `end` over `duration` seconds."""

    def __init__(self, start, end, duration, ease=ease_out_cubic, on_complete=None):
        self.start = start
        self.end = end
        self.duration = max(duration, 1e-6)
        self.ease = ease
        self.elapsed = 0.0
        self.done = False
        self.on_complete = on_complete

    def update(self, dt):
        if self.done:
            return self.end
        self.elapsed += dt
        t = min(self.elapsed / self.duration, 1.0)
        if t >= 1.0:
            self.done = True
            if self.on_complete:
                self.on_complete()
        eased = self.ease(t)
        return self.start + (self.end - self.start) * eased

    @property
    def value(self):
        t = min(self.elapsed / self.duration, 1.0)
        return self.start + (self.end - self.start) * self.ease(t)


class Timer:
    """Simple countdown timer with an on_complete callback."""

    def __init__(self, duration, on_complete=None, repeat=False):
        self.duration = duration
        self.elapsed = 0.0
        self.on_complete = on_complete
        self.repeat = repeat
        self.done = False

    def update(self, dt):
        if self.done:
            return
        self.elapsed += dt
        if self.elapsed >= self.duration:
            if self.repeat:
                self.elapsed = 0.0
            else:
                self.done = True
            if self.on_complete:
                self.on_complete()

    @property
    def progress(self):
        return min(self.elapsed / self.duration, 1.0)

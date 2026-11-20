"""Timing curves: easing functions, windows and keyframe interpolation used by every item and the camera."""
from __future__ import annotations

import bisect
import math


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def window(t, start, length):
    """0 before `start`, 1 after `start + length`, linear in between."""
    if length <= 0:
        return 1.0 if t >= start else 0.0
    return clamp((t - start) / length)


def ease_out(u):
    u = clamp(u)
    return 1.0 - (1.0 - u) ** 3


def ease_in_out(u):
    u = clamp(u)
    return u * u * (3.0 - 2.0 * u)


def overshoot(u, k=1.5):
    """Ease out that passes the target a little and settles (for things that land)."""
    u = clamp(u) - 1.0
    return 1.0 + u * u * ((k + 1.0) * u + k)


class Keys:
    """Interpolates (time, value) keys with a shape-preserving cubic: it never overshoots a key, and
    two equal neighbouring keys make it come to rest (so a camera settles where it is asked to)."""

    def __init__(self, pairs):
        pairs = sorted(pairs, key=lambda p: p[0])
        merged = []
        for t, v in pairs:              # same time twice: the later key wins
            if merged and abs(merged[-1][0] - t) < 1e-9:
                merged[-1] = (t, v)
            else:
                merged.append((t, v))
        self.ts = [p[0] for p in merged]
        self.vs = [p[1] for p in merged]
        n = len(merged)
        slopes = [(self.vs[i + 1] - self.vs[i]) / (self.ts[i + 1] - self.ts[i]) for i in range(n - 1)]
        tang = [0.0] * n
        for i in range(n):
            if i == 0:
                tang[i] = slopes[0] if slopes else 0.0
            elif i == n - 1:
                tang[i] = slopes[-1]
            else:
                a, b = slopes[i - 1], slopes[i]
                if a == 0 or b == 0 or (a > 0) != (b > 0):
                    tang[i] = 0.0
                else:                   # weighted harmonic mean keeps the curve monotone between keys
                    ha, hb = self.ts[i] - self.ts[i - 1], self.ts[i + 1] - self.ts[i]
                    w1, w2 = 2 * hb + ha, hb + 2 * ha
                    tang[i] = (w1 + w2) / (w1 / a + w2 / b)
        if n > 1 and slopes:
            for i in (0, n - 1):        # end tangents: never steeper than 3x the neighbouring slope
                s = slopes[0] if i == 0 else slopes[-1]
                if s == 0 or (tang[i] > 0) != (s > 0):
                    tang[i] = 0.0
                elif abs(tang[i]) > 3 * abs(s):
                    tang[i] = 3 * s
        self.tang = tang

    def __call__(self, t):
        ts = self.ts
        if len(ts) == 1 or t <= ts[0]:
            return self.vs[0]
        if t >= ts[-1]:
            return self.vs[-1]
        i = bisect.bisect_right(ts, t) - 1
        h = ts[i + 1] - ts[i]
        s = (t - ts[i]) / h
        s2, s3 = s * s, s * s * s
        return ((2 * s3 - 3 * s2 + 1) * self.vs[i] + (s3 - 2 * s2 + s) * h * self.tang[i]
                + (-2 * s3 + 3 * s2) * self.vs[i + 1] + (s3 - s2) * h * self.tang[i + 1])


class Drift:
    """Slow, smooth, never-repeating wobble from a seed: the hand-held feel of a camera operator."""

    def __init__(self, seed=3, parts=4):
        import random
        r = random.Random(seed)
        self.parts = [(r.uniform(0.25, 2.2), r.uniform(0, math.tau), r.uniform(0.4, 1.0)) for _ in range(parts)]
        self.norm = sum(p[2] for p in self.parts)

    def __call__(self, t):
        return sum(a * math.sin(f * t + ph) for f, ph, a in self.parts) / self.norm

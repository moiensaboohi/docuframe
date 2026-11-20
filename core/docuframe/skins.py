"""Skins: the visual vocabulary styles choose from. A style's "skin" block picks one option per role:

  ground   texture | flat | gradient, plus an optional pattern: grid | dots | halftone | lines | paper
  panel    paper | card | torn | outline | glass | sticky
  photo    pinned | cutout | frame | polaroid | full | tape
  title    bar | kinetic | stack | serif | torn
  number   counter | ring | bar
  motion   drop | pop | slide | wipe | slap       (how things enter)
  accents  none | shapes | scraps | halftone | corners
  source   plain | chip          lower_third  bar | chip | line        letterbox  true | false

Every item here is drawn in code and follows the same rules as the engine's items: entrance motion
from the style, colours from the style's tokens, text through the shaping layer (any script).
"""
from __future__ import annotations

import math

import numpy as np
import skia

from . import engine as E
from .motion import clamp, ease_in_out, ease_out, overshoot, window


# ---------------------------------------------------------------- entrance motion
def enter(c, motion, u, w, h):
    """Apply a style's entrance to the canvas (already translated to the item's centre).
    Returns the opacity to use; u is the entrance progress 0..1."""
    if u >= 1:
        return 1.0
    if motion == "pop":
        k = 0.86 + 0.14 * overshoot(u, 2.2)
        c.scale(k, k)
        return min(1.0, u * 2.5)
    if motion == "slide":
        c.translate(0, (1 - ease_out(u)) * h * 0.12)
        return ease_out(u)
    if motion == "wipe":
        e = ease_in_out(u)
        c.clipRect(skia.Rect.MakeLTRB(-w / 2 - 400, -h / 2 - 400, -w / 2 - 400 + (w + 800) * e, h / 2 + 400))
        return 1.0
    if motion == "slap":
        k = 1.0 + 0.12 * (1 - ease_out(u))
        c.scale(k, k)
        c.rotate((1 - ease_out(u)) * -4)
        return min(1.0, u * 4)
    # drop (default): settle from slightly above and bigger
    k = 1.0 + 0.06 * (1 - ease_out(u))
    c.translate(0, -(1 - ease_out(u)) * 60)
    c.scale(k, k)
    return min(1.0, u * 1.8)


def torn_outline(w, h, seed, rough=0.012, step=34):
    """A rectangle with hand-torn edges: a slow wander plus fine fibres, like paper ripped by hand.
    rough scales the wander relative to the short side; never spiky."""
    rnd = np.random.default_rng(seed)
    amp = min(w, h) * rough * 1.6 + 6
    fine = 14.0
    pts = []
    for (x0, y0), (x1, y1) in (((-w / 2, -h / 2), (w / 2, -h / 2)), ((w / 2, -h / 2), (w / 2, h / 2)),
                               ((w / 2, h / 2), (-w / 2, h / 2)), ((-w / 2, h / 2), (-w / 2, -h / 2))):
        n = max(4, int(math.hypot(x1 - x0, y1 - y0) / fine))
        nx, ny = -(y1 - y0), (x1 - x0)
        ln = math.hypot(nx, ny) or 1
        nx, ny = nx / ln, ny / ln
        # slow wander: smoothed random walk, pinned to zero at the corners
        walk = np.cumsum(rnd.normal(0, 1, n))
        walk -= np.linspace(walk[0], walk[-1], n)
        k = max(3, n // 12)
        walk = np.convolve(walk, np.ones(k) / k, mode="same")
        walk = walk / (np.abs(walk).max() or 1) * amp
        jag = rnd.normal(0, 1, n) * amp * 0.18
        for i in range(n):
            f = i / n
            j = walk[i] + jag[i]
            pts.append(skia.Point(x0 + (x1 - x0) * f + nx * j, y0 + (y1 - y0) * f + ny * j))
    p = skia.Path()
    p.addPoly(pts, True)
    return p


def _paper_noise(seed=3, n=256):
    rnd = np.random.default_rng(seed)
    v = rnd.random((n, n)).astype(np.float32)
    v = (v * 0.5 + np.roll(v, 1, 0) * 0.25 + np.roll(v, 1, 1) * 0.25)
    g = (200 + 55 * v).astype(np.uint8)
    rgba = np.dstack([g, g, g, np.full_like(g, 255)])
    return skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.ColorType.kRGBA_8888_ColorType)


_NOISE = {}


def paper_shader(scale=3.0):
    if "img" not in _NOISE:
        _NOISE["img"] = _paper_noise()
    return _NOISE["img"].makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat, E.SMOOTH, skia.Matrix.Scale(scale, scale))


# ---------------------------------------------------------------- panels
class Card(E.Item):
    """A surface for text: card (rounded, soft shadow), paper (flat, soft shadow), torn (torn paper,
    hard shadow, fibre texture), outline (thick ink border, solid offset shadow), glass (translucent,
    thin luminous edge), sticky (sticky note with tape)."""
    z, enter = 11, 0.5

    def __init__(self, x, y, w, h, t_in, rgb, skin="card", motion="pop", rot=0.0, accent=None, ink=(20, 20, 20), seed=1, t_out=None, sfx=True):
        self.x, self.y = x, y
        super().__init__(t_in, t_out, None, sfx)
        self.w, self.h, self.rgb, self.skin, self.motion, self.rot, self.accent, self.ink = w, h, rgb, skin, motion, rot, accent, ink
        self.reach = max(w, h) * 0.8 + 300
        self.outline = torn_outline(w, h, seed) if skin in ("torn", "sticky") else None

    def cues(self):
        return [("paper" if self.skin in ("torn", "sticky", "paper") else "tick", self.t_in, 0.5, {})]

    def paint(self, c, kit, t, o):
        u = self.entered(t)
        if u <= 0:
            return
        c.save()
        c.translate(self.x, self.y)
        c.rotate(self.rot)
        o *= enter(c, self.motion, u, self.w, self.h)
        w, h = self.w, self.h
        box = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h)
        s = self.skin
        if s == "card":
            rr = skia.RRect.MakeRectXY(box, 56, 56)
            c.drawRRect(skia.RRect.MakeRectXY(box.makeOffset(0, 46), 56, 56), E.fill((0, 0, 0), 0.16 * o, 70))
            c.drawRRect(rr, E.fill(self.rgb, o))
            if self.accent:
                c.save()
                c.clipRRect(rr, True)
                c.drawRect(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, 30), E.fill(self.accent, o))
                c.restore()
        elif s == "outline":
            stroke = max(14.0, min(w, h) * 0.012)
            rr = skia.RRect.MakeRectXY(box, 28, 28)
            c.drawRRect(skia.RRect.MakeRectXY(box.makeOffset(stroke * 2.4, stroke * 2.4), 28, 28), E.fill(self.ink, o))
            c.drawRRect(rr, E.fill(self.rgb, o))
            c.drawRRect(rr, E.line(self.ink, o, stroke))
        elif s == "glass":
            rr = skia.RRect.MakeRectXY(box, 40, 40)
            c.drawRRect(rr, E.fill(self.rgb, 0.62 * o))
            edge = self.accent or (255, 255, 255)
            c.drawRRect(rr, E.line(edge, 0.55 * o, 5))
            c.drawRRect(rr, E.line(edge, 0.18 * o, 26, 18))
        elif s in ("torn", "sticky"):
            path = self.outline
            shadow = skia.Path(path)
            shadow.offset(22, 30)
            c.drawPath(shadow, E.fill((0, 0, 0), 0.35 * o, 4))
            c.drawPath(path, E.fill(self.rgb, o))
            c.save()
            c.clipPath(path, skia.ClipOp.kIntersect, True)
            c.drawPaint(skia.Paint(Shader=paper_shader(), BlendMode=skia.BlendMode.kMultiply, Alphaf=0.35 * o))
            c.restore()
            if s == "sticky":
                tape = skia.Rect.MakeXYWH(-w * 0.18, -h / 2 - 50, w * 0.36, 110)
                c.save()
                c.rotate(-3)
                c.drawRect(tape, E.fill((245, 240, 222), 0.75 * o))
                c.restore()
        else:   # paper
            c.drawRect(box.makeOffset(26, 40), E.fill((0, 0, 0), 0.35 * o, 50))
            c.drawRect(box, E.fill(self.rgb, o))
            if self.accent:
                c.drawRect(skia.Rect.MakeXYWH(-w / 2, -h / 2, 26, h), E.fill(self.accent, o))
        c.restore()


# ---------------------------------------------------------------- photos
class Photo(E.Item):
    """A photograph in a style's treatment: pinned | cutout | frame | polaroid | full | tape | outline | glass."""
    z, enter = 10, 0.5

    def __init__(self, key, x, y, w, t_in, skin="frame", motion="drop", rot=0.0, label=None, label_t=None, caption=None,
                 bar_rgb=(176, 24, 20), ink=(20, 20, 20), paper=(250, 248, 242), seed=2, t_out=None, sfx=True):
        self.x, self.y = x, y
        super().__init__(t_in, t_out, None, sfx)
        self.key, self.w, self.skin, self.motion, self.rot = key, w, skin, motion, rot
        self.label, self.label_t, self.caption, self.bar_rgb, self.ink, self.paper = label, label_t, caption, bar_rgb, ink, paper
        self.seed = seed
        self.reach = w * 1.3 + 600
        self._torn = None

    def size(self, meta):
        info = meta.get(self.key)
        if info is None:
            raise SystemExit(f"Photo {self.key} is not prepared: list it in photos.json and run docuframe assets.")
        return self.w, self.w * info["h"] / info["w"]

    size_from = size

    def cues(self):
        return [("drop" if self.skin in ("pinned", "polaroid", "tape") else "paper", self.t_in, 0.6, {})] + \
               ([("tick", self.label_t, 0.4, {})] if self.label and self.label_t is not None else [])

    def paint(self, c, kit, t, o):
        u = self.entered(t)
        if u <= 0:
            return
        img = kit.image(self.key)
        w = self.w
        h = w * img.height() / img.width()
        pic = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h)
        c.save()
        c.translate(self.x, self.y)
        c.rotate(self.rot)
        o *= enter(c, self.motion, u, w, h)
        s = self.skin
        ip = skia.Paint(Alphaf=o)
        if s == "cutout":
            if self._torn is None:
                self._torn = torn_outline(w + w * 0.07, h + w * 0.07, self.seed, rough=0.01, step=26)
            shadow = skia.Path(self._torn)
            shadow.offset(20, 28)
            c.drawPath(shadow, E.fill((0, 0, 0), 0.4 * o, 4))
            c.drawPath(self._torn, E.fill(self.paper, o))
            c.drawImageRect(img, pic, E.SMOOTH, ip)
        elif s == "frame":
            rr = skia.RRect.MakeRectXY(pic, 40, 40)
            c.drawRRect(skia.RRect.MakeRectXY(pic.makeOffset(0, 50), 40, 40), E.fill((0, 0, 0), 0.28 * o, 80))
            c.save()
            c.clipRRect(rr, True)
            c.drawImageRect(img, pic, E.SMOOTH, ip)
            c.restore()
            c.drawRRect(rr, E.line((255, 255, 255), 0.25 * o, 4))
        elif s == "outline":           # neo-brutal: thick ink border, solid offset block shadow
            bw = max(14.0, w * 0.012)
            off = w * 0.03
            c.drawRect(pic.makeOffset(off, off), E.fill(self.ink, o))
            c.drawImageRect(img, pic, E.SMOOTH, ip)
            c.drawRect(pic, E.line(self.ink, o, bw))
        elif s == "glass":             # dark tech: rounded, thin luminous edge, deep soft shadow
            rr = skia.RRect.MakeRectXY(pic, 28, 28)
            c.drawRRect(skia.RRect.MakeRectXY(pic.makeOffset(0, 60), 28, 28), E.fill((0, 0, 0), 0.5 * o, 110))
            c.save()
            c.clipRRect(rr, True)
            c.drawImageRect(img, pic, E.SMOOTH, ip)
            c.restore()
            c.drawRRect(rr, E.line(self.bar_rgb, 0.55 * o, 5))
        elif s == "full":
            c.drawRect(pic.makeOffset(0, 40), E.fill((0, 0, 0), 0.5 * o, 90))
            c.drawImageRect(img, pic, E.SMOOTH, ip)
        elif s == "polaroid":
            pad, foot = w * 0.05, w * 0.2
            frame = skia.Rect.MakeLTRB(-w / 2 - pad, -h / 2 - pad, w / 2 + pad, h / 2 + foot)
            c.drawRect(frame.makeOffset(24, 36), E.fill((0, 0, 0), 0.4 * o, 40))
            c.drawRect(frame, E.fill(self.paper, o))
            c.drawImageRect(img, pic, E.SMOOTH, ip)
            if self.caption or self.label:
                txt = self.caption or self.label
                size = foot * 0.42
                E.draw_text(c, kit, txt, 0, h / 2 + foot * 0.62, size, "hand", self.ink, o * window(t, self.t_in + 0.5, 0.5), 0, "center")
        elif s == "tape":
            c.drawRect(pic.makeOffset(16, 26), E.fill((0, 0, 0), 0.35 * o, 30))
            edge = w * 0.025
            c.drawRect(pic.makeOutset(edge, edge), E.fill(self.paper, o))
            c.drawImageRect(img, pic, E.SMOOTH, ip)
            for sx, ang in ((-1, -38), (1, 38)):
                c.save()
                c.translate(sx * w / 2, -h / 2)
                c.rotate(ang)
                c.drawRect(skia.Rect.MakeXYWH(-w * 0.09, -w * 0.025, w * 0.18, w * 0.05), E.fill((236, 230, 200), 0.78 * o))
                c.restore()
        else:   # pinned
            edge = w * 0.035
            frame = pic.makeOutset(edge, edge)
            c.drawRect(frame.makeOffset(18, 36), E.fill((0, 0, 0), 0.45 * o, 45))
            c.drawRect(frame, E.fill((241, 237, 227), o))
            c.drawImageRect(img, pic, E.SMOOTH, ip)
            E.pushpin(c, 0, -h / 2 - edge * 0.45, max(24.0, w * 0.018), (188, 32, 28), o)
        c.restore()
        if self.label and self.label_t is not None and s != "polaroid":
            grow = ease_out(window(t, self.label_t, 0.35))
            if grow > 0:
                below = -h * 0.2 if s == "full" else h / 2 + w * 0.06 + 120    # full-frame: the label sits inside the picture
                bx, by = E.turn(self.x, self.y, 0, below if s != "full" else h * 0.28, self.rot)
                r, g, b = self.bar_rgb[:3]
                light = 0.2126 * r + 0.7152 * g + 0.0722 * b > 150
                E.tag(c, kit, self.label, bx, by, max(90.0, w * 0.042), o, grow, self.bar_rgb, (18, 18, 18) if light else (250, 248, 244))


# ---------------------------------------------------------------- type
class Kinetic(E.Item):
    """Modern title motion: each word rises out of a mask, staggered; an accent rule wipes in under it.
    Joined or right-to-left scripts rise as one line (letters never appear half-joined)."""
    z = 70

    def __init__(self, text, x, y, size, t_in, rgb, font="display", accent=None, rule=True, stagger=0.07, t_out=None, sfx=True):
        self.x, self.y = x, y
        super().__init__(t_in, t_out, None, sfx)
        self.text, self.size, self.rgb, self.font, self.accent, self.rule, self.stagger = text, size, rgb, font, accent, rule, stagger
        self.reach = len(text) * size * 0.7 + size * 3

    def cues(self):
        return [("whoosh", self.t_in, 0.3, {}), ("tick", self.t_in + 0.35, 0.3, {})]

    def paint(self, c, kit, t, o):
        from .fonts import detect_scripts
        if t < self.t_in:
            return
        total = E.text_width(kit, self.text, self.size, self.font, 0.0)
        left = self.x - total / 2
        line_top, line_bottom = self.y - self.size * 1.05, self.y + self.size * 0.3
        simple = not (detect_scripts(self.text) - {"latin"})
        words = self.text.split(" ") if simple else [self.text]
        space = E.text_width(kit, " ", self.size, self.font, 0.0) if simple else 0
        x = left
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(left - self.size, line_top, left + total + self.size, line_bottom))
        for k, word in enumerate(words):
            ww = E.text_width(kit, word, self.size, self.font, 0.0)
            u = ease_out(window(t, self.t_in + k * self.stagger, 0.55))
            if u > 0:
                rise = (1 - u) * self.size * 1.25
                E.draw_text(c, kit, word, x if simple else self.x, self.y + rise, self.size, self.font, self.rgb, o, 0.0,
                            "left" if simple else "center")
            x += ww + space
        c.restore()
        if self.rule and self.accent:
            k = ease_in_out(window(t, self.t_in + 0.25 + len(words) * self.stagger, 0.5))
            if k > 0:
                c.drawRect(skia.Rect.MakeXYWH(left, self.y + self.size * 0.32, total * k, self.size * 0.09), E.fill(self.accent, o))


class Kicker(E.Item):
    """A small label chip above a title or number (the 'eyebrow' of modern editorial design)."""
    z = 72

    def __init__(self, text, x, y, size, t_in, bg, fg, motion="pop", t_out=None):
        self.x, self.y = x, y
        super().__init__(t_in, t_out, None, False)
        self.text, self.size, self.bg, self.fg, self.motion = text, size, bg, fg, motion

    def paint(self, c, kit, t, o):
        u = self.entered(t)
        if u <= 0:
            return
        w = E.text_width(kit, self.text, self.size, "label", 0.12) + self.size * 1.6
        h = self.size * 1.9
        c.save()
        c.translate(self.x, self.y)
        o *= enter(c, self.motion, u, w, h)
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h), h / 2, h / 2), E.fill(self.bg, o))
        E.draw_text(c, kit, self.text, 0, self.size * 0.36, self.size, "label", self.fg, o, 0.12, "center")
        c.restore()


class Rule(E.Item):
    """Thin horizontal rules either side of a line of text (elegant serif titles)."""
    z = 69

    def __init__(self, x, y, gap, length, t_in, rgb, width=6, t_out=None):
        self.x, self.y = x, y
        super().__init__(t_in, t_out, None, False)
        self.gap, self.length, self.rgb, self.width = gap, length, rgb, width

    def paint(self, c, kit, t, o):
        k = ease_in_out(window(t, self.t_in, 0.8))
        if k <= 0:
            return
        for s in (-1, 1):
            a = self.x + s * self.gap
            c.drawLine(a, self.y, a + s * self.length * k, self.y, E.line(self.rgb, 0.8 * o, self.width))


# ---------------------------------------------------------------- numbers
class Gauge(E.Item):
    """A ring that sweeps to a share (0..1) around a number, or a bar that fills under it."""
    z = 65

    def __init__(self, x, y, size, share, t_in, rgb, track_rgb, kind="ring", dur=1.3, t_out=None):
        self.x, self.y = x, y
        super().__init__(t_in, t_out, None, False)
        self.size, self.share, self.rgb, self.track, self.kind, self.dur = size, clamp(share), rgb, track_rgb, kind, dur

    def paint(self, c, kit, t, o):
        k = ease_out(window(t, self.t_in, self.dur)) * self.share
        a = o * window(t, self.t_in, 0.3)
        if a <= 0:
            return
        if self.kind == "ring":
            r = self.size
            box = skia.Rect.MakeXYWH(self.x - r, self.y - r, 2 * r, 2 * r)
            width = r * 0.09
            c.drawArc(box, 0, 360, False, E.line(self.track, 0.35 * a, width))
            if k > 0:
                c.drawArc(box, -90, 360 * k, False, E.line(self.rgb, a, width))
        else:
            w, h = self.size * 2.4, self.size * 0.11
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(self.x - w / 2, self.y, w, h), h / 2, h / 2), E.fill(self.track, 0.35 * a))
            if k > 0:
                c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(self.x - w / 2, self.y, w * k, h), h / 2, h / 2), E.fill(self.rgb, a))


# ---------------------------------------------------------------- accents and ground
class Accents(E.Item):
    """Decoration around a cluster: shapes (rings, dots, pluses), scraps (torn paper), halftone patch,
    or corners (viewfinder brackets). Pops in staggered, then holds."""
    z = 5

    def __init__(self, kind, x, y, w, h, t_in, palette, seed=0, t_out=None):
        self.x, self.y = x, y
        super().__init__(t_in, t_out, None, False)
        self.kind, self.w, self.h, self.palette = kind, w, h, [tuple(p) for p in palette]
        self.reach = max(w, h)
        rnd = np.random.default_rng(seed)
        self.bits = []
        if kind in ("shapes", "scraps"):
            # composed, not sprinkled: a small cluster in two opposite corners of the frame, partly bleeding off
            flip = 1 if seed % 2 else -1
            corners = [(-0.47, -0.40), (0.47, -0.36)] if flip > 0 else [(-0.47, -0.40), (-0.46, 0.24)]   # never bottom-right: sources live there
            shapes = ["ring", "dot", "plus", "ring"]
            k = 0
            for ci, (fx, fy) in enumerate(corners):
                for j in range(2 if kind == "shapes" else 1):
                    ox = (rnd.uniform(0.04, 0.09) if j else 0) * (-1 if fx > 0 else 1)
                    oy = (rnd.uniform(0.05, 0.1) if j else 0) * (-1 if fy > 0 else 1)
                    big = rnd.uniform(170, 260) if j == 0 else rnd.uniform(60, 110)
                    self.bits.append({"x": (fx + ox) * w, "y": (fy + oy) * h, "s": big if kind == "shapes" else rnd.uniform(600, 950),
                                      "shape": shapes[(seed + k) % 4] if j == 0 else "dot", "col": self.palette[k % len(self.palette)],
                                      "rot": rnd.uniform(-25, 25), "delay": 0.15 + k * 0.08, "seed": int(rnd.integers(1, 999))})
                    k += 1

    def paint(self, c, kit, t, o):
        if self.kind == "corners":
            k = ease_out(window(t, self.t_in, 0.45))
            if k <= 0:
                return
            arm = min(self.w, self.h) * 0.12
            pad = 1 + 0.08 * (1 - k)
            col = self.palette[0]
            for sx in (-1, 1):
                for sy in (-1, 1):
                    cx, cy = self.x + sx * self.w / 2 * pad, self.y + sy * self.h / 2 * pad
                    p = skia.Path()
                    p.moveTo(cx, cy - sy * arm)
                    p.lineTo(cx, cy)
                    p.lineTo(cx - sx * arm, cy)
                    c.drawPath(p, E.line(col, 0.9 * o * k, 10, cap=skia.Paint.kSquare_Cap))
            return
        if self.kind == "halftone":
            k = ease_out(window(t, self.t_in, 0.6))
            if k <= 0:
                return
            col, step = self.palette[0], 70
            cx0, cy0 = self.x + self.w * 0.35, self.y - self.h * 0.3
            for i in range(-8, 9):
                for j in range(-6, 7):
                    d = math.hypot(i / 8, j / 6)
                    r = (1 - d) * step * 0.42 * k
                    if r > 2:
                        c.drawCircle(cx0 + i * step, cy0 + j * step, r, E.fill(col, 0.5 * o))
            return
        for b in self.bits:
            u = window(t, self.t_in + b["delay"], 0.45)
            if u <= 0:
                continue
            x, y, s = self.x + b["x"], self.y + b["y"], b["s"]
            c.save()
            c.translate(x, y)
            c.rotate(b["rot"])
            k = overshoot(u, 2.0) if self.kind == "shapes" else ease_out(u)
            c.scale(k, k)
            if self.kind == "scraps":
                path = torn_outline(s, s * 0.6, b["seed"], rough=0.02, step=40)
                c.drawPath(path, E.fill(b["col"], 0.92 * o))
                c.save()
                c.clipPath(path, skia.ClipOp.kIntersect, True)
                c.drawPaint(skia.Paint(Shader=paper_shader(), BlendMode=skia.BlendMode.kMultiply, Alphaf=0.35 * o))
                c.restore()
            elif b["shape"] == "ring":
                c.drawCircle(0, 0, s / 2, E.line(b["col"], o, s * 0.12))
            elif b["shape"] == "dot":
                c.drawCircle(0, 0, s / 3, E.fill(b["col"], o))
            else:
                arm, th = s / 2, s * 0.14
                c.drawRect(skia.Rect.MakeXYWH(-arm, -th / 2, 2 * arm, th), E.fill(b["col"], o))
                c.drawRect(skia.Rect.MakeXYWH(-th / 2, -arm, th, 2 * arm), E.fill(b["col"], o))
            c.restore()


class Ground(E.Item):
    """A pattern on the background that moves with the camera: grid, dots, lines or paper fibre."""
    z = -90

    def __init__(self, pattern, rgb, alpha=0.08, step=240):
        super().__init__(-1.0)
        self.pattern, self.rgb, self.alpha, self.step = pattern, tuple(rgb), alpha, step

    def bounds(self, kit):
        return None

    def paint(self, c, kit, t, o):
        v, s = kit.view, self.step
        x0, x1 = math.floor(v.left() / s) * s, math.ceil(v.right() / s) * s
        y0, y1 = math.floor(v.top() / s) * s, math.ceil(v.bottom() / s) * s
        if self.pattern == "paper":
            c.drawRect(v, skia.Paint(Shader=paper_shader(6.0), BlendMode=skia.BlendMode.kMultiply, Alphaf=self.alpha * 4))
        elif self.pattern == "grid":
            p = E.line(self.rgb, self.alpha, 3)
            for x in np.arange(x0, x1 + s, s):
                c.drawLine(x, y0, x, y1, p)
            for y in np.arange(y0, y1 + s, s):
                c.drawLine(x0, y, x1, y, p)
        elif self.pattern == "lines":
            p = E.line(self.rgb, self.alpha, 3)
            for y in np.arange(y0, y1 + s, s / 2):
                c.drawLine(x0, y, x1, y, p)
        elif self.pattern in ("dots", "halftone"):
            p = E.fill(self.rgb, self.alpha)
            r = 7 if self.pattern == "dots" else 16
            pts = [skia.Point(float(x), float(y)) for x in np.arange(x0, x1 + s, s) for y in np.arange(y0, y1 + s, s)]
            pp = skia.Paint(p)
            pp.setStrokeWidth(r * 2)
            pp.setStrokeCap(skia.Paint.kRound_Cap)
            c.drawPoints(skia.Canvas.kPoints_PointMode, pts, pp)


# ---------------------------------------------------------------- overlays (screen space)
class Letterbox(E.Item):
    """Cinema bars top and bottom (about 2.39:1) for the cinematic styles."""
    z = 190

    def __init__(self, duration, ratio=2.39):
        super().__init__(-1.0)
        self.ratio = ratio

    def draw(self, c, kit, t):
        W, H = kit.overlay_size
        if H > W:
            return
        bar = max(0.0, (H - W / self.ratio) / 2)
        c.drawRect(skia.Rect.MakeXYWH(0, 0, W, bar), E.fill((0, 0, 0)))
        c.drawRect(skia.Rect.MakeXYWH(0, H - bar, W, bar), E.fill((0, 0, 0)))


class SourceTag(E.Item):
    """The on-screen source line: plain text with a soft shadow, or a pill chip."""
    z = 200

    def __init__(self, text, t_in, t_out, skin, fg, bg, letterbox=False):
        super().__init__(t_in, t_out, None, False)
        self.text, self.skin, self.fg, self.bg, self.letterbox = text, skin, fg, bg, letterbox

    def draw(self, c, kit, t):
        a = window(t, self.t_in + 0.3, 0.4) * self.fade(t)
        if a <= 0:
            return
        W, H = kit.overlay_size
        tall = H > W
        size = 26
        bottom = H - (H * 0.24 if tall else (max(0.0, (H - W / 2.39) / 2) + 34 if self.letterbox else 56))
        width = E.text_width(kit, self.text, size, "label", 0.02)
        x = W / 2 if tall else W - 60 - width / 2
        if self.skin == "chip":
            pad = 18
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - width / 2 - pad, bottom - size * 1.15, width + 2 * pad, size * 1.7),
                                              size, size), E.fill(self.bg, 0.85 * a))
            E.draw_text(c, kit, self.text, x, bottom, size, "label", self.fg, a, 0.02, "center")
        else:
            E.draw_text(c, kit, self.text, x + 1.5, bottom + 1.5, size, "label", (0, 0, 0), 0.6 * a, 0.02, "center")
            E.draw_text(c, kit, self.text, x, bottom, size, "label", self.fg, 0.92 * a, 0.02, "center")


class NameTag(E.Item):
    """Lower third: bar (bold colour bar), chip (rounded, modern), or line (thin rule, elegant)."""
    z = 210

    def __init__(self, name, role, t_in, t_out, skin, accent, fg=(250, 248, 244), panel=(20, 20, 20)):
        super().__init__(t_in, t_out, None, False)
        self.name, self.role, self.skin, self.accent, self.fg, self.panel = name, role, skin, accent, fg, panel

    def draw(self, c, kit, t):
        u = ease_out(window(t, self.t_in, 0.5)) * self.fade(t)
        if u <= 0:
            return
        W, H = kit.overlay_size
        tall = H > W
        x, y = (70, H * 0.70) if tall else (90, H - 190)
        nw = E.text_width(kit, self.name, 46, "cond", 0.03)
        if self.skin == "line":
            c.drawRect(skia.Rect.MakeXYWH(x, y + 18, (nw + 40) * u, 4), E.fill(self.accent, u))
            E.draw_text(c, kit, self.name, x, y, 46, "cond", self.fg, u, 0.03)
            if self.role:
                E.draw_text(c, kit, self.role, x, y + 62, 28, "label", self.fg, 0.8 * u, 0.04)
            return
        if self.skin == "chip":
            w = nw + 70
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y - 60, w * u, 84), 42, 42), E.fill(self.panel, 0.92 * u))
            c.drawCircle(x + 34, y - 18, 12 * u, E.fill(self.accent, u))
            E.draw_text(c, kit, self.name, x + 58, y, 42, "cond", self.fg, window(u, 0.5, 0.5), 0.03)
            if self.role:
                E.draw_text(c, kit, self.role, x + 12, y + 56, 28, "label", self.panel if self.panel[0] > 128 else self.fg, 0.9 * u, 0.04)
            return
        c.drawRect(skia.Rect.MakeXYWH(x, y - 58, (nw + 60) * u, 76), E.fill(self.accent, 0.95 * u))
        if u > 0.6:
            E.draw_text(c, kit, self.name, x + 30, y, 46, "cond", self.fg, (u - 0.6) / 0.4, 0.04)
        if self.role:
            rw = E.text_width(kit, self.role, 28, "label") + 50
            c.drawRect(skia.Rect.MakeXYWH(x, y + 22, rw * u, 50), E.fill(self.panel, 0.88 * u))
            if u > 0.7:
                E.draw_text(c, kit, self.role, x + 25, y + 56, 28, "label", (235, 235, 235), (u - 0.7) / 0.3)

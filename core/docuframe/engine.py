"""docuframe engine.

A film is a set of Items placed in a world, a camera that moves over that world, and a Renderer.

World space is measured in "board units": a 3840-wide frame at camera zoom 1 shows 3840 of them.
Every Item has an entrance time and (optionally) an exit time; the base class turns time into an
opacity and hands it to the item's `paint`, so items only describe what they look like. The camera
is curves (centre, zoom, roll) that settle on each key; hard cuts start new curves. A frame:
camera matrix -> items (culled to the view) -> spotlight -> finish (glow, tone curve, vignette,
grade, grain, fades) -> screen-space overlays.

Nothing here knows style names; scenes.py turns film.json + a style into Items and camera keys.
"""
from __future__ import annotations

import json
import math
import pathlib

import numpy as np
import skia
from PIL import Image

from .motion import Drift, Keys, clamp, ease_in_out, ease_out, overshoot, window

ramp, ease_out_cubic, ease_out_back = window, ease_out, overshoot

FONT_ROLES = {
    "cond": ["Oswald", "Bebas Neue", "Arial Narrow", "DejaVu Sans Condensed"],
    "label": ["Montserrat", "Helvetica Neue", "Arial", "DejaVu Sans"],
    "labelm": ["Montserrat", "Helvetica Neue", "Arial", "DejaVu Sans"],
    "serif": ["Libre Baskerville", "Georgia", "Times New Roman", "DejaVu Serif"],
    "mono": ["Courier Prime", "Courier New", "DejaVu Sans Mono"],
    "hand": ["Homemade Apple", "Segoe Script", "DejaVu Sans"],
}
SMOOTH = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)
NEAREST = skia.SamplingOptions()


# ---------------------------------------------------------------- small drawing vocabulary
def colour(rgb, alpha=1.0):
    r, g, b = (int(v) for v in rgb[:3])
    return skia.Color(r, g, b, int(round(255 * clamp(alpha))))


def fill(rgb, alpha=1.0, soften=0.0):
    p = skia.Paint(AntiAlias=True, Color=colour(rgb, alpha))
    if soften:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, soften))
    return p


def line(rgb, alpha, width, soften=0.0, cap=skia.Paint.kRound_Cap):
    p = fill(rgb, alpha, soften)
    p.setStyle(skia.Paint.kStroke_Style)
    p.setStrokeWidth(width)
    p.setStrokeCap(cap)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def paint(rgb=(0, 0, 0), a=1.0, stroke=None, blur=None, aa=True):
    """For scene items: a fill, or a stroke when `stroke` is a width."""
    return line(rgb, a, stroke, blur or 0.0) if stroke is not None else fill(rgb, a, blur or 0.0)


def draw_text(c, kit, text, x, y, size, font="serif", rgb=(240, 240, 240), a=1.0, track=0.0, align="left", reveal=None):
    """One shaped line of any script, baseline at y (see docuframe.text)."""
    return kit.book.draw(c, text, x, y, size, font, rgb, a, track, align, reveal)


def text_width(kit, text, size, font="serif", track=0.0):
    return kit.book.width(text, size, font, track)


def drawn_part(path, share):
    """The first `share` of a path's length, as if a pen were still drawing it. (Every stroke the
    engine draws is a single contour, so one measure covers it.)"""
    if share >= 1.0:
        return path
    piece = skia.Path()
    if share > 0.0:
        gauge = skia.PathMeasure(path, False)
        gauge.getSegment(0.0, gauge.getLength() * share, piece, True)
    return piece


def turn(px, py, ox, oy, degrees):
    """Offset (ox, oy) from (px, py), rotated by `degrees`, in world coordinates."""
    s, c = math.sin(math.radians(degrees)), math.cos(math.radians(degrees))
    return px + ox * c - oy * s, py + ox * s + oy * c


def worn_ink(seed=11, size=(1024, 512)):
    """Alpha mask of small specks; erasing it from type or stamps makes them look printed and worn."""
    rnd = np.random.default_rng(seed)
    w, h = size
    dots = rnd.random((h // 2, w // 2)) ** 18
    big = np.asarray(Image.fromarray((np.clip(dots * 4, 0, 1) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC))
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[..., 3] = big
    return skia.Image.fromarray(rgba, colorType=skia.ColorType.kRGBA_8888_ColorType)


# ---------------------------------------------------------------- the project as the film sees it
def _letter_count(s):
    return sum(ch.isalpha() for ch in s)


def _plain(s):
    return "".join(ch for ch in s.lower() if ch.isalnum() or ch.isspace()).strip()


class Doc:
    """Narration timing, photo sizes and map data of one project folder."""

    def __init__(self, project):
        root = pathlib.Path(project).resolve()
        timing_file = root / "audio" / "timing.json"
        if not timing_file.exists():
            raise SystemExit(f"No narration timing in {root.name} yet. Run docuframe voice, then docuframe narration.")
        self.dir, self.prep = root, root / "assets" / "prep"
        self.timing = json.loads(timing_file.read_text(encoding="utf-8"))
        self.duration = self.timing["total_duration"]
        self.seg = {s["id"]: s for s in self.timing["segments"]}
        self._meta, self._kit = None, None

    @property
    def meta(self):
        if self._meta is None:
            f = self.prep / "photos" / "meta.json"
            self._meta = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        return self._meta

    def _line(self, n):
        try:
            return self.seg[n]
        except KeyError:
            raise SystemExit(f"film.json uses narration line {n}; the script's lines are {sorted(self.seg)}.") from None

    def L(self, n):
        return self._line(n)["start"]

    def E(self, n):
        return self._line(n)["end"]

    def W(self, n, word, nth=0):
        """Time at which `word` is spoken in line n (aligned if available, else estimated)."""
        seg = self._line(n)
        target = _plain(word).split()
        if seg.get("words") and target:
            spoken = [_plain(w["w"]) for w in seg["words"]]
            exact = [k for k in range(len(spoken)) if spoken[k:k + len(target)] == target]
            found = exact or [k for k, s in enumerate(spoken) if target[0] in s]
            if nth < len(found):
                return seg["words"][found[nth]]["start"]
        text = seg["vo"]
        at = -1
        for _ in range(nth + 1):
            at = text.lower().find(word.lower(), at + 1)
            if at == -1:
                raise SystemExit(f'"{word}" does not occur in line {n} as spoken ({text!r}). '
                                 "Pick a word from the spoken text; numbers there are written out in words.")
        share = _letter_count(text[:at]) / max(1, _letter_count(text))
        return seg["start"] + share * (seg["end"] - seg["start"]) + 0.04

    def on(self, photo, fx, fy):
        w, h = photo.size(self.meta)
        return turn(photo.x, photo.y, (fx - 0.5) * w, (fy - 0.5) * h, photo.rot)

    def res(self):
        if self._kit is None:
            self._kit = Res(1.0, self.prep, self.dir / "fonts")
        return self._kit

    @property
    def _res(self):
        return self._kit

    @_res.setter
    def _res(self, kit):
        self._kit = kit

    def map(self, name):
        f = self.prep / f"map_{name}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        raise SystemExit(f'Map "{name}" has not been built. Add it to map.json and run docuframe map.')


class Res:
    """What drawing needs at hand: images sized for the output, fonts, the current view."""

    def __init__(self, scale, prep=None, fonts_dir=None, roles=None, lang=None):
        from .text import FontBook
        self.scale, self.prep = scale, pathlib.Path(prep) if prep else None
        self.book = FontBook({**FONT_ROLES, **(roles or {})}, fonts_dir, lang)
        self.screen_scale, self.overlay_size = 1.0, (1920, 1080)
        self.view = skia.Rect.MakeLTRB(-1e7, -1e7, 1e7, 1e7)
        self.meta = {}
        self._cache = {}

    def image(self, key, longest=None):
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        if self.prep is None:
            raise SystemExit("This film uses images but was built without a project folder.")
        path = self.prep / key if "." in key else self.prep / "photos" / f"{key}.jpg"
        if not path.exists():
            raise SystemExit(f"Image {key} is not prepared ({path.name}). Run docuframe assets.")
        pic = Image.open(path).convert("RGBA")
        limit = int(max(512, (longest or 2400) * max(self.scale, 0.3)))
        pic.thumbnail((limit, limit), Image.LANCZOS)        # keep only the pixels the frame can show
        img = skia.Image.fromarray(np.ascontiguousarray(np.asarray(pic)), colorType=skia.ColorType.kRGBA_8888_ColorType)
        self._cache[key] = img = img.withDefaultMipmaps()
        return img

    def wear(self):
        if "__wear" not in self._cache:
            self._cache["__wear"] = worn_ink()
        return self._cache["__wear"]


# ---------------------------------------------------------------- items
class Item:
    """Base for everything in the world.

    Subclasses set class attributes and implement paint(c, kit, t, opacity):
      z      drawing order          enter  seconds the entrance takes
      reach  culling radius         sound  (kind, gain) played at t_in, or None
    """
    z, enter, reach, sound, LEAVE = 0, 0.35, 2500.0, None, 0.6

    def __init__(self, t_in=0.0, t_out=None, z=None, sfx=True):
        self.t_in, self.t_out, self.sfx = t_in, t_out, sfx
        self.x = getattr(self, "x", 0.0)
        self.y = getattr(self, "y", 0.0)
        if z is not None:
            self.z = z

    def entered(self, t, length=None):
        return window(t, self.t_in, self.enter if length is None else length)

    def fade(self, t):
        return 1.0 if self.t_out is None else 1.0 - window(t, self.t_out, self.LEAVE)

    def visible(self, t):
        if t < self.t_in - 0.02:
            return False
        return self.t_out is None or t < self.t_out + self.LEAVE

    def bounds(self, kit):
        r = self.reach
        return skia.Rect.MakeLTRB(self.x - r, self.y - r, self.x + r, self.y + r)

    def cues(self):
        return [(self.sound[0], self.t_in, self.sound[1], {})] if self.sound else []

    def shakes(self):
        return []

    def draw(self, c, kit, t):
        o = self.fade(t)
        if o > 0:
            self.paint(c, kit, t, o)

    def paint(self, c, kit, t, opacity):
        raise NotImplementedError


class Board(Item):
    """The surface: one texture, tiled under whatever the camera can see."""
    z = -100

    def __init__(self, texture, tile=2400):
        super().__init__(-1.0)
        self.texture, self.tile = texture, tile

    def bounds(self, kit):
        return None

    def paint(self, c, kit, t, o):
        img, step, v = kit.image(self.texture, longest=self.tile), self.tile, kit.view
        for j in range(math.floor(v.top() / step), math.ceil(v.bottom() / step)):
            for i in range(math.floor(v.left() / step), math.ceil(v.right() / step)):
                c.drawImageRect(img, skia.Rect.MakeXYWH(i * step, j * step, step + 1, step + 1), SMOOTH)


def pushpin(c, x, y, size, rgb, o):
    c.drawOval(skia.Rect.MakeXYWH(x - size * 0.6, y - size * 0.2, size * 2.2, size * 1.6), fill((0, 0, 0), 0.3 * o, size * 0.45))
    c.drawCircle(x, y, size, fill(rgb, o))
    c.drawCircle(x - size * 0.35, y - size * 0.35, size * 0.3, fill((255, 240, 236), 0.5 * o))


def tag(c, kit, text, cx, cy, size, o, grow, bar_rgb, ink_rgb):
    """A name bar: a colour bar that grows from the left, then its text."""
    width = text_width(kit, text, size, "cond", 0.05) + size
    height = size * 1.3
    c.drawRect(skia.Rect.MakeXYWH(cx - width / 2, cy - height / 2, width * grow, height), fill(bar_rgb, 0.95 * o))
    letters = window(grow, 0.5, 0.5)
    if letters > 0:
        draw_text(c, kit, text, cx, cy + size * 0.36, size, "cond", ink_rgb, o * letters, 0.05, "center")


class Print(Item):
    """A photograph on the board: border, shadow, a pin, and a short drop into place."""
    z, enter, sound = 10, 0.45, ("drop", 0.6)

    def __init__(self, key, x, y, w, rot=0.0, t_in=0.0, t_out=None, border=0.035, pin=True, label=None, label_t=None,
                 label_rgb=(176, 24, 20), aspect=None, z=None, sfx=True):
        self.x, self.y = x, y
        super().__init__(t_in, t_out, z, sfx)
        self.key, self.w, self.rot, self.border, self.pin = key, w, rot, border, pin
        self.label, self.label_t, self.label_rgb, self.aspect = label, label_t, label_rgb, aspect
        self.reach = w * 1.2 + 600

    def size(self, meta):
        if self.aspect:
            return self.w, self.w / self.aspect
        info = meta.get(self.key)
        if info is None:
            raise SystemExit(f"Photo {self.key} is not prepared: list it in photos.json and run docuframe assets.")
        return self.w, self.w * info["h"] / info["w"]

    size_from = size

    def cues(self):
        extra = [("tick", self.label_t, 0.4, {})] if self.label and self.label_t is not None else []
        return super().cues() + extra

    def paint(self, c, kit, t, o):
        drop = ease_out(self.entered(t))
        o *= min(1.0, drop * 1.6)
        if o <= 0:
            return
        img = kit.image(self.key)
        w = self.w
        h = w / self.aspect if self.aspect else w * img.height() / img.width()
        edge = w * self.border
        sheet = skia.Rect.MakeLTRB(-w / 2 - edge, -h / 2 - edge, w / 2 + edge, h / 2 + edge)
        c.save()
        c.translate(self.x, self.y)
        c.rotate(self.rot + (1 - drop) * 3.0)
        c.scale(1.0 + (1 - drop) * 0.08, 1.0 + (1 - drop) * 0.08)
        lift = 120 * (1 - drop) + 36
        c.drawRect(sheet.makeOffset(lift * 0.5, lift), fill((0, 0, 0), 0.45 * o, 45 + 50 * (1 - drop)))
        c.drawRect(sheet, fill((241, 237, 227), o))
        c.drawImageRect(img, skia.Rect.MakeLTRB(-w / 2, -h / 2, w / 2, h / 2), SMOOTH, skia.Paint(Alphaf=o))
        if self.pin:
            pushpin(c, 0, -h / 2 - edge * 0.45, max(24.0, w * 0.018), (188, 32, 28), o)
        c.restore()
        if self.label and self.label_t is not None:
            grow = ease_out(window(t, self.label_t, 0.35))
            if grow > 0:
                bx, by = turn(self.x, self.y, 0, h / 2 + edge + 150, self.rot)
                tag(c, kit, self.label, bx, by, max(90.0, w * 0.045), o, grow, self.label_rgb, (250, 246, 238))


class StringLine(Item):
    """Red string pulled from one pin to another, sagging a little under its own weight."""
    z = 30

    def __init__(self, a, b, t_in, dur=0.9, rgb=(176, 28, 24), width=9, sag=0.06, pins=True, t_out=None, sfx=True):
        self.x, self.y = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        super().__init__(t_in, t_out, None, sfx)
        self.a, self.b, self.dur, self.rgb, self.width, self.pins = a, b, dur, rgb, width, pins
        span = math.hypot(b[0] - a[0], b[1] - a[1])
        self.reach = span * 0.6 + 500
        self.curve = skia.Path()
        self.curve.moveTo(*a)
        self.curve.quadTo(self.x, self.y + span * sag, *b)

    def cues(self):
        return [("string", self.t_in, 0.5, {"dur": self.dur})]

    def paint(self, c, kit, t, o):
        pulled = ease_in_out(window(t, self.t_in, self.dur))
        if pulled <= 0:
            return
        part = drawn_part(self.curve, pulled)
        shadow = skia.Path(part)
        shadow.offset(6, 14)
        c.drawPath(shadow, line((0, 0, 0), 0.3 * o, self.width, 6))
        c.drawPath(part, line(self.rgb, o, self.width))
        if self.pins:
            pushpin(c, self.a[0], self.a[1], 26, (188, 32, 28), o)
            if pulled > 0.98:
                pushpin(c, self.b[0], self.b[1], 26, (188, 32, 28), o)


class PenMark(Item):
    """A mark drawn by hand onto the board: ellipse, underline, arrow, strike, or highlight (marker)."""
    z = 50

    def __init__(self, kind, x, y, w, h=0, t_in=0.0, dur=0.6, width=14, seed=1, rot=0.0, t_out=None, rgb=(170, 26, 22), z=None, sfx=True):
        self.x, self.y = x, y
        super().__init__(t_in, t_out, z, sfx)
        self.kind, self.w, self.h, self.dur, self.width, self.rot, self.rgb = kind, w, h, dur, width, rot, rgb
        self.reach = max(w, h) + 200
        self.stroke = self._shape(np.random.default_rng(seed))

    def _shape(self, rnd):
        w, h, p = self.w, self.h, skia.Path()
        if self.kind == "ellipse":           # a quick pen loop that overshoots where it began
            a0 = rnd.uniform(-2.6, -2.0)
            pts = [(math.cos(a0 + k * 0.095) * w / 2 * (1 + 0.03 * math.sin(k * 0.3)),
                    math.sin(a0 + k * 0.095) * h / 2 * (1 + 0.02 * k / 70)) for k in range(72)]
            p.moveTo(*pts[0])
            for q in pts[1:]:
                p.lineTo(*q)
        elif self.kind == "arrow":
            p.moveTo(-w / 2, h * 0.4)
            p.cubicTo(-w / 6, -h * 0.5, w / 6, -h * 0.5, w / 2, 0)
        else:
            bow = (h or 24) * rnd.uniform(-0.15, 0.15)
            p.moveTo(-w / 2, rnd.uniform(-5, 5))
            p.quadTo(0, bow, w / 2, rnd.uniform(-5, 5))
        return p

    def cues(self):
        return [("marker" if self.kind == "highlight" else "pen", self.t_in, 0.6, {"dur": self.dur})]

    def paint(self, c, kit, t, o):
        done = ease_out(window(t, self.t_in, self.dur))
        if done <= 0:
            return
        c.save()
        c.translate(self.x, self.y)
        c.rotate(self.rot)
        part = drawn_part(self.stroke, done)
        if self.kind == "highlight":
            marker = line((246, 206, 46), 0.6 * o, self.width, cap=skia.Paint.kButt_Cap)
            marker.setBlendMode(skia.BlendMode.kMultiply)
            c.drawPath(part, marker)
        else:
            c.drawPath(part, line(self.rgb, 0.92 * o, self.width))
            if self.kind == "arrow" and done > 0.95:
                k, tip = self.width * 3.4, skia.Path()
                tip.moveTo(self.w / 2 - k, -k * 0.7)
                tip.lineTo(self.w / 2, 0)
                tip.lineTo(self.w / 2 - k * 0.9, k * 0.8)
                c.drawPath(tip, line(self.rgb, 0.92 * o, self.width))
        c.restore()


class Stamp(Item):
    """A rubber stamp hitting the board: it lands big and settles, with a jolt and a thud."""
    z, sound = 80, ("impact", 0.9)

    def __init__(self, text, x, y, size=150, rot=-8.0, t_in=0.0, t_out=None, rgb=(170, 28, 24), z=None, sfx=True):
        self.x, self.y = x, y
        super().__init__(t_in, t_out, z, sfx)
        self.text, self.size, self.rot, self.rgb = text, size, rot, rgb
        self.reach = len(text) * size + 400

    def shakes(self):
        return [(self.t_in + 0.05, 16.0, 0.3)]

    def paint(self, c, kit, t, o):
        hit = window(t, self.t_in, 0.16)
        if hit <= 0:
            return
        o *= min(1.0, hit * 3)
        k = 1.0 + 0.7 * (1 - ease_out(hit))
        box_w = text_width(kit, self.text, self.size, "cond", 0.06) + self.size * 0.9
        box_h = self.size * 1.5
        box = skia.Rect.MakeXYWH(-box_w / 2, -box_h / 2, box_w, box_h)
        c.save()
        c.translate(self.x, self.y)
        c.rotate(self.rot)
        c.scale(k, k)
        c.saveLayer(box.makeOutset(box_w, box_h), None)
        c.drawRect(box, line(self.rgb, 0.88 * o, self.size * 0.1))
        draw_text(c, kit, self.text, 0, self.size * 0.36, self.size, "cond", self.rgb, 0.88 * o, 0.06, "center")
        c.drawImageRect(kit.wear(), box, SMOOTH, skia.Paint(BlendMode=skia.BlendMode.kDstOut))
        c.restore()
        c.restore()


class BigText(Item):
    """Headline type in the world. bar: a colour block wiped in behind it; grunge: worn ink;
    type_on: seconds to type it out; hit: thud gain on arrival."""
    z, enter = 70, 0.35

    def __init__(self, text, x, y, size, t_in, t_out=None, font="cond", rgb=(246, 243, 236), track=0.04, type_on=0.0,
                 shadow=True, grunge=True, bar=None, bar_h=0.9, hit=None, z=None, sfx=True, rules=False, shadow_rgb=(0, 0, 0)):
        self.x, self.y = x, y
        super().__init__(t_in, t_out, z, sfx)
        self.text, self.size, self.font, self.rgb, self.track = text, size, font, rgb, track
        self.type_on, self.grunge, self.bar, self.bar_h, self.hit = type_on, grunge, bar, bar_h, hit
        self.shadow = 0.5 if shadow is True else float(shadow or 0)
        self.shadow_rgb = tuple(shadow_rgb)
        self.reach = len(text) * size * 0.7 + size * 3

    def cues(self):
        out = [("impact", self.t_in, self.hit, {})] if self.hit else []
        return out + ([("type", self.t_in, 0.5, {"dur": self.type_on})] if self.type_on else [])

    def paint(self, c, kit, t, o):
        alpha = o * self.entered(t)
        if alpha <= 0:
            return
        shown = len(self.text) * window(t, self.t_in, self.type_on) if self.type_on else None
        width = text_width(kit, self.text, self.size, self.font, self.track)
        mid = self.y - self.size * 0.36
        if self.bar is not None:
            grow = ease_out(window(t, self.t_in - 0.1, 0.4))
            pad, tall = self.size * 0.35, self.size * self.bar_h
            c.drawRect(skia.Rect.MakeXYWH(self.x - width / 2 - pad, mid - tall / 2, (width + 2 * pad) * grow, tall), fill(self.bar, 0.95 * o))
        if self.shadow:
            draw_text(c, kit, self.text, self.x + self.size * 0.03, self.y + self.size * 0.04, self.size, self.font,
                      self.shadow_rgb, self.shadow * alpha, self.track, "center", shown)
        area = skia.Rect.MakeXYWH(self.x - width / 2 - self.size, mid - self.size, width + 2 * self.size, self.size * 2)
        if self.grunge:
            c.saveLayer(area, None)
        draw_text(c, kit, self.text, self.x, self.y, self.size, self.font, self.rgb, alpha, self.track, "center", shown)
        if self.grunge:
            c.drawImageRect(kit.wear(), area, SMOOTH, skia.Paint(BlendMode=skia.BlendMode.kDstOut, Alphaf=0.7))
            c.restore()


class Counter(Item):
    """A number counting up to its value; decimals follow the value; optional caption under it."""
    z, enter = 70, 0.25

    def __init__(self, x, y, size, value, t_in, dur=1.3, prefix="", suffix="", caption=None, rgb=(246, 206, 46), t_out=None,
                 font="cond", start=0, decimals=None, sfx=True, shadow=0.45, shadow_rgb=(0, 0, 0), caption_font="cond",
                 caption_rgb=None, caption_gap=0.45, caption_size=None, caption_max=None):
        self.x, self.y = x, y
        self.shadow, self.shadow_rgb, self.caption_font = float(shadow or 0), tuple(shadow_rgb), caption_font
        self.caption_rgb, self.caption_gap = caption_rgb, caption_gap
        self.caption_size, self.caption_max = caption_size, caption_max
        super().__init__(t_in, t_out, None, sfx)
        self.size, self.value, self.dur, self.prefix, self.suffix = size, value, dur, prefix, suffix
        self.caption, self.rgb, self.font, self.start = caption, rgb, font, start
        if decimals is None:
            frac = repr(float(value)).split(".")[1]
            decimals = 0 if frac == "0" else min(3, len(frac))
        self.decimals = decimals
        self.reach = size * 6

    def cues(self):
        return [("roll", self.t_in, 0.5, {"dur": self.dur}), ("impact", self.t_in + self.dur, 0.5, {})]

    def paint(self, c, kit, t, o):
        alpha = o * self.entered(t)
        if alpha <= 0:
            return
        now = self.start + (self.value - self.start) * ease_out(window(t, self.t_in, self.dur))
        label = f"{self.prefix}{now:,.{self.decimals}f}{self.suffix}"
        layers = ((self.size * 0.03, self.size * 0.04, self.shadow_rgb, self.shadow),) if self.shadow > 0 else ()
        for dx, dy, rgb, a in layers + ((0, 0, self.rgb, 1.0),):
            draw_text(c, kit, label, self.x + dx, self.y + dy, self.size, self.font, rgb, a * alpha, 0.02, "center")
        if self.caption:
            under = alpha * window(t, self.t_in + 0.4, 0.4)
            cs = self.caption_size or self.size * 0.24
            if self.caption_max:
                cw = text_width(kit, self.caption, cs, self.caption_font, 0.1)
                if cw > self.caption_max:
                    cs *= self.caption_max / cw
            draw_text(c, kit, self.caption, self.x, self.y + self.size * self.caption_gap, cs, self.caption_font,
                      self.caption_rgb or self.rgb, 0.9 * under, 0.1, "center")


class PaperDoc(Item):
    """A document recreated in code: heading lines, grey bars where body text would be (never invented
    words), and an optional block of real text whose phrases can be highlighted."""
    z, enter, sound = 12, 0.5, ("paper", 0.6)

    def __init__(self, x, y, w, h, rot=0.0, t_in=0.0, t_out=None, header=(), rows=16, sentence=None, sentence_row=6,
                 sentence_size=64, seed=4, pin=True, z=None, sfx=True):
        self.x, self.y = x, y
        super().__init__(t_in, t_out, z, sfx)
        self.w, self.h, self.rot, self.header, self.rows = w, h, rot, list(header), rows
        self.sentence, self.first_row, self.text_size, self.pin = sentence, sentence_row, sentence_size, pin
        self.bar_lengths = list(np.random.default_rng(seed).uniform(0.5, 0.95, rows))
        self.row_step = h * 0.62 / max(1, rows)
        self.reach = max(w, h)
        self._wrapped = None

    def row_y(self, i):
        return -self.h * 0.22 + i * self.row_step

    def lines(self, kit):
        if self._wrapped is None:
            self._wrapped, words = [], (self.sentence or "").split()
            while words:
                take = len(words)
                while take > 1 and text_width(kit, " ".join(words[:take]), self.text_size, "serif") > self.w * 0.8:
                    take -= 1
                self._wrapped.append(" ".join(words[:take]))
                words = words[take:]
        return self._wrapped

    def phrase_spans(self, kit, phrase):
        """[(world centre, width)] of a phrase in the text block, one per wrapped line it touches."""
        want, spans = phrase.lower(), []
        for i, text in enumerate(self.lines(kit)):
            low = text.lower()
            start, piece = low.find(want), want
            if start < 0:
                for n in range(len(want) - 1, 3, -1):
                    if low.endswith(want[:n]):
                        start, piece = len(low) - n, want[:n]
                        break
                    if low.startswith(want[-n:]):
                        start, piece = 0, want[-n:]
                        break
            if start < 0:
                continue
            left = -self.w * 0.4 + text_width(kit, text[:start], self.text_size, "serif")
            width = text_width(kit, text[start:start + len(piece)], self.text_size, "serif")
            centre = turn(self.x, self.y, left + width / 2, self.row_y(self.first_row + i) - self.text_size * 0.3, self.rot)
            spans.append((centre, width))
        return spans

    def paint(self, c, kit, t, o):
        settle = ease_out(self.entered(t))
        o *= settle
        if o <= 0:
            return
        c.save()
        c.translate(self.x, self.y + 80 * (1 - settle))
        c.rotate(self.rot)
        sheet = skia.Rect.MakeXYWH(-self.w / 2, -self.h / 2, self.w, self.h)
        c.drawRect(sheet.makeOffset(24, 40), fill((0, 0, 0), 0.4 * o, 50))
        c.drawRect(sheet, fill((242, 236, 222), o))
        y = -self.h * 0.41
        for k, heading in enumerate(self.header):
            size = self.w * (0.05 if k == 0 else 0.03)
            draw_text(c, kit, heading, 0, y + size, size, "mono", (40, 34, 28), o, 0.05, "center")
            y += size * 1.6
        text = self.lines(kit)
        for i in range(self.rows):
            k = i - self.first_row
            if 0 <= k < len(text):
                draw_text(c, kit, text[k], -self.w * 0.4, self.row_y(i), self.text_size, "serif", (32, 28, 24), o)
            else:
                c.drawRect(skia.Rect.MakeXYWH(-self.w * 0.4, self.row_y(i) - self.row_step * 0.2, self.w * 0.8 * self.bar_lengths[i],
                                              self.row_step * 0.22), fill((150, 144, 134), 0.55 * o))
        if self.pin:
            pushpin(c, 0, -self.h / 2 + 40, 28, (188, 32, 28), o)
        c.restore()


# ---------------------------------------------------------------- maps
MAP_LOOKS = {
    "explainer": {"water": (150, 190, 196), "land": (210, 204, 192), "line": (150, 142, 130), "frame": (70, 66, 62)},
    "period": {"water": (190, 200, 186), "land": (222, 206, 172), "line": (126, 96, 66), "frame": (104, 80, 56)},
    "night": {"water": (20, 30, 48), "land": (44, 52, 66), "line": (90, 104, 126), "frame": (120, 130, 150)},
}


class GeoMap(Item):
    """A printed map from docuframe map data, recorded once as vectors so it stays sharp at any zoom.
    A projection unit becomes K board units; `origin` is where (0, 0) lands."""

    def __init__(self, data, K, origin=(0, 0), look="explainer", t_in=-1):
        super().__init__(t_in)
        self.data, self.K, self.origin = data, K, origin
        self.look = MAP_LOOKS[look] if isinstance(look, str) else look
        x0, y0, x1, y1 = data["frame"]
        self.rect = skia.Rect.MakeLTRB(*self.w((x0, y0)), *self.w((x1, y1)))
        self._picture = None

    def w(self, p):
        return self.origin[0] + p[0] * self.K, self.origin[1] + p[1] * self.K

    def path_of(self, name):
        shape = skia.Path()
        for ring in self.data["regions"][name]:
            shape.addPoly([skia.Point(*self.w(q)) for q in ring], True)
        return shape

    def bounds(self, kit):
        return self.rect

    def paint(self, c, kit, t, o):
        if self._picture is None:
            rec = skia.PictureRecorder()
            pc = rec.beginRecording(self.rect.makeOutset(400, 400))
            look, stroke = self.look, max(2.0, self.K * 0.0015)
            pc.drawRect(self.rect.makeOffset(30, 50), fill((0, 0, 0), 0.4, 60))
            pc.drawRect(self.rect, fill(look["water"]))
            pc.save()
            pc.clipRect(self.rect)
            for name in self.data["regions"]:
                shape = self.path_of(name)
                pc.drawPath(shape, fill(look["land"]))
                pc.drawPath(shape, line(look["line"], 0.9, stroke))
            pc.restore()
            pc.drawRect(self.rect, line(look["frame"], 1.0, stroke * 3))
            self._picture = rec.finishRecordingAsPicture()
        c.drawPicture(self._picture)


class RegionFill(Item):
    """Map regions tinted in a colour as they are named."""
    z, enter, sound = 2, 0.6, ("swell", 0.4)

    def __init__(self, geomap, names, rgb, t_in, t_out=None, alpha=0.9):
        super().__init__(t_in, t_out)
        missing = [n for n in names if n not in geomap.data["regions"]]
        if missing:
            raise SystemExit(f"Map regions not found: {missing}. Names in this map include: {', '.join(sorted(geomap.data['regions'])[:15])}")
        self.shape = skia.Path()
        for n in names:
            self.shape.addPath(geomap.path_of(n))
        self.rgb, self.alpha = rgb, alpha

    def bounds(self, kit):
        return self.shape.getBounds()

    def paint(self, c, kit, t, o):
        k = o * ease_in_out(self.entered(t))
        if k > 0:
            c.drawPath(self.shape, fill(self.rgb, self.alpha * k))


class Route(Item):
    """A journey drawn from a to b, ending in an arrowhead."""
    z = 40

    def __init__(self, a, b, t_in, dur=1.2, bend=0.15, width=12, rgb=(176, 28, 24), t_out=None, sfx=True):
        super().__init__(t_in, t_out, None, sfx)
        self.b, self.dur, self.width, self.rgb = b, dur, width, rgb
        ctrl = ((a[0] + b[0]) / 2 - (b[1] - a[1]) * bend, (a[1] + b[1]) / 2 + (b[0] - a[0]) * bend)
        self.track = skia.Path()
        self.track.moveTo(*a)
        self.track.quadTo(*ctrl, *b)
        self.heading = math.atan2(b[1] - ctrl[1], b[0] - ctrl[0])

    def bounds(self, kit):
        return self.track.getBounds().makeOutset(500, 500)

    def cues(self):
        return [("pen", self.t_in, 0.5, {"dur": self.dur})]

    def paint(self, c, kit, t, o):
        done = ease_in_out(window(t, self.t_in, self.dur))
        if done <= 0:
            return
        c.drawPath(drawn_part(self.track, done), line(self.rgb, o, self.width))
        if done >= 0.99:
            k, head = self.width * 4, skia.Path()
            head.moveTo(self.b[0] - k * math.cos(self.heading - 0.45), self.b[1] - k * math.sin(self.heading - 0.45))
            head.lineTo(*self.b)
            head.lineTo(self.b[0] - k * math.cos(self.heading + 0.45), self.b[1] - k * math.sin(self.heading + 0.45))
            c.drawPath(head, line(self.rgb, o, self.width))


# ---------------------------------------------------------------- the film and its camera
class Film:
    """What happens, when: items, overlays, camera and spotlight keys, cuts, jolts and sound cues."""

    def __init__(self, duration, fps=30, look=None):
        self.duration, self.fps = duration, fps
        self.look = {"board": "cork_dark.png", **(look or {})}
        self.items = [Board(self.look["board"])] if self.look.get("board") else []
        self.handheld = float(self.look.get("handheld", 1.0))
        self.overlays, self.cuts, self.jolts, self.sfx = [], [], [], []
        self.cam_keys, self.focus_keys = [], []
        self.fade_in, self.fade_out, self.auto_cues = 0.8, 2.0, True
        self.roles = self.lang = None
        self._curves = None
        self._hand = (Drift(5), Drift(9), Drift(13))

    def add(self, item):
        self.items.append(item)
        self.jolts.extend(item.shakes())
        return item

    def overlay(self, item):
        """A screen-space item, drawn after the finish. Units: the frame's short side is 1080."""
        self.overlays.append(item)
        return item

    def cam(self, t, x, y, zoom, rot=0.0):
        self.cam_keys.append((t, x, y, zoom, rot))
        self._curves = None

    def focus(self, t, x, y, radius, strength=0.55):
        self.focus_keys.append((t, x, y, radius, strength))
        self._curves = None

    def shot(self, t, x, y, zoom, rot=0.0, radius=None, strength=0.55):
        """Camera and spotlight on the same point at time t."""
        self.cam(t, x, y, zoom, rot)
        self.focus(t, x, y, radius or 1700 / zoom, strength)

    def cut(self, t):
        self.cuts.append(t)
        self._curves = None

    def shake(self, t, amp=14.0, dur=0.3):
        self.jolts.append((t, amp, dur))

    def cue(self, kind, t, gain=1.0, **extra):
        self.sfx.append({"type": kind, "t": round(t, 3), "gain": gain, **extra})

    def _make_curves(self, keys, logzoom):
        """One set of curves per stretch between hard cuts: [(from_time, [curve per channel])]."""
        edges = [-math.inf, *sorted(self.cuts), math.inf]
        out = []
        for lo, hi in zip(edges, edges[1:]):
            chunk = sorted(k for k in keys if lo <= k[0] < hi)
            if chunk:
                times, *channels = zip(*chunk)
                channels = [list(v) for v in channels]
                if logzoom:
                    channels[2] = [math.log(z) for z in channels[2]]
                out.append((lo, [Keys(list(zip(times, v))) for v in channels]))
        return out

    def _stretch(self, which, t):
        if self._curves is None:
            if not self.cam_keys:
                raise SystemExit("The film has no camera keys.")
            self._curves = (self._make_curves(self.cam_keys, True), self._make_curves(self.focus_keys, False))
        chosen = None
        for start, curves in self._curves[which]:
            if chosen is None or t >= start:
                chosen = curves
        return chosen

    def camera(self, t):
        x, y, logz, roll = (k(t) for k in self._stretch(0, t))
        zoom = math.exp(logz)
        dx, dy, dr = self._hand
        hh = self.handheld
        sx, sy = 9 * hh * dx(t), 7 * hh * dy(t)     # hand-held drift, in 4K screen pixels
        for start, amp, length in self.jolts:
            if start <= t < start + length:
                left = amp * (1 - (t - start) / length) ** 2
                sx += left * math.sin(70 * (t - start))
                sy += left * math.cos(55 * (t - start))
        return x + sx / zoom, y + sy / zoom, zoom, roll + 0.15 * hh * dr(0.7 * t)

    def focus_at(self, t):
        curves = self._stretch(1, t) if self.focus_keys else None
        return tuple(k(t) for k in curves) if curves else None

    def screen_speed(self, t):
        step = 1.0 / self.fps
        if any(t < c <= t + step for c in self.cuts):
            t -= step
        a, b = self.camera(t), self.camera(t + step)
        return math.hypot(b[0] - a[0], b[1] - a[1]) * a[2] + abs(math.log(b[2] / a[2])) * 1920 + abs(b[3] - a[3]) * 33.5

    def all_cues(self):
        out = list(self.sfx)

        def near(kind, t):
            return any(q["type"] == kind and abs(q["t"] - t) < 0.15 for q in out)
        if self.auto_cues:
            for it in self.items:
                for kind, t, gain, extra in (it.cues() if it.sfx else []):
                    if 0 <= t <= self.duration and not near(kind, t):
                        out.append({"type": kind, "t": round(t, 3), "gain": gain, **extra})
            last = -10.0
            for n in range(0, int(self.duration * self.fps), 2):
                t = n / self.fps
                speed = self.screen_speed(t)
                if speed > 80 and t - last > 1.5 and not near("whoosh", t):
                    out.append({"type": "whoosh", "t": round(max(0.0, t - 0.08), 3), "gain": round(min(0.8, 0.25 + speed / 700), 2)})
                    last = t
        return sorted(out, key=lambda q: q["t"])


def _surface(w, h):
    return skia.Surface.MakeRaster(skia.ImageInfo.Make(w, h, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kPremul_AlphaType))


class Renderer:
    """Turns a Film into frames. frame(n) -> RGBA (H, W, 4) uint8; frame_rgb(n) -> RGB."""

    def __init__(self, film: Film, width=1920, height=1080, doc: Doc | None = None):
        self.film, self.W, self.H = film, width, height
        self.s = max(width, height) / 3840.0
        self.res = Res(self.s, doc.prep if doc else None, (doc.dir / "fonts") if doc else None, roles=film.roles, lang=film.lang)
        if doc:
            self.res.meta = doc.meta
        self.items = sorted(film.items, key=lambda it: it.z)
        self.world, self.blend, self.final = _surface(width, height), _surface(width, height), _surface(width, height)
        self.tw, self.th = max(1, width // 8), max(1, height // 8)
        self.tiny, self.tiny_blur = _surface(self.tw, self.th), _surface(self.tw, self.th)
        self._prepare_finish(film.look)

    def _prepare_finish(self, look):
        w, h = self.W, self.H
        self.bright_pass = skia.ColorFilters.Matrix([1.6, 0, 0, 0, -0.99, 0, 1.6, 0, 0, -0.99, 0, 0, 1.6, 0, -0.99, 0, 0, 0, 1, 0])
        self.soften = skia.Paint(ImageFilter=skia.ImageFilters.Blur(6, 6, skia.TileMode.kClamp))
        k = float(look.get("curve", 0.0))
        x = np.linspace(0.0, 1.0, 256)
        lut = np.rint(np.clip((1 - k) * x + k * x * x * (3 - 2 * x), 0, 1) * 255).astype(np.uint8)
        self.tone = skia.Paint(ColorFilter=skia.TableColorFilter.Make(lut.tolist()))
        gy, gx = np.ogrid[0:h, 0:w]
        dist = np.sqrt(((gx + 0.5) / w - 0.5) ** 2 + ((gy + 0.5) / h - 0.5) ** 2) / math.sqrt(0.5)
        light = np.clip(1.0 - float(look.get("vignette", 0.0)) * np.clip((dist - 0.3) / 0.7, 0, 1) ** 1.6, 0.25, 1.0)
        light = light[..., None] * np.asarray(look.get("grade", (1, 1, 1)), np.float32)
        plate = np.concatenate([np.clip(light * 255, 0, 255).astype(np.uint8), np.full((h, w, 1), 255, np.uint8)], axis=2)
        self.vignette = skia.Image.fromarray(np.ascontiguousarray(plate), colorType=skia.ColorType.kRGBA_8888_ColorType)
        rnd = np.random.default_rng(7)
        self.grain = []
        for _ in range(6 if w * h <= 2_500_000 else 3):
            noise = np.clip(128 + 40 * rnd.standard_normal((h // 2 + 1, w // 2 + 1)), 0, 255).astype(np.uint8)
            full = np.asarray(Image.fromarray(noise).resize((w, h), Image.BILINEAR))
            self.grain.append(skia.Image.fromarray(np.ascontiguousarray(np.stack([full, full, full, np.full_like(full, 255)], -1)),
                                                   colorType=skia.ColorType.kRGBA_8888_ColorType))

    def view_matrix(self, t):
        cx, cy, zoom, roll = self.film.camera(t)
        k = zoom * self.s
        m = skia.Matrix.Translate(self.W / 2, self.H / 2)
        m.preScale(k, k)
        m.preRotate(roll)
        m.preTranslate(-cx, -cy)
        reach_x, reach_y = self.W / 2 / k * 1.3, self.H / 2 / k * 1.3
        return m, k, skia.Rect.MakeLTRB(cx - reach_x, cy - reach_y, cx + reach_x, cy + reach_y)

    def draw_world(self, t):
        f, kit = self.film, self.res
        m, kit.screen_scale, kit.view = self.view_matrix(t)
        with self.world as c:
            c.clear(colour(f.look.get("bg", (10, 10, 10))))
            if f.look.get("bg2"):            # soft radial light behind everything (screen space)
                glow = skia.GradientShader.MakeRadial(skia.Point(self.W * 0.5, self.H * 0.42), max(self.W, self.H) * 0.75,
                                                      [colour(f.look["bg2"]), colour(f.look["bg"])], [0.0, 1.0])
                c.drawPaint(skia.Paint(Shader=glow))
            c.save()
            c.concat(m)
            for it in self.items:
                if it.visible(t):
                    box = it.bounds(kit)
                    if box is None or skia.Rect.Intersects(box, kit.view):
                        it.draw(c, kit, t)
            c.restore()
            spot = f.focus_at(t) if f.look.get("spotlight", 1.0) > 0 else None
            if spot:                      # spotlight in screen space, around the projected focus point
                fx, fy, radius, strength = spot
                strength *= f.look.get("spotlight", 1.0)
                centre = m.mapXY(fx, fy)
                r = max(10.0, radius * 2.5 * kit.screen_scale)
                tint = f.look.get("dim", (6, 5, 4))
                shade = skia.GradientShader.MakeRadial(centre, r, [colour(tint, 0), colour(tint, 0), colour(tint, clamp(strength)),
                                                                   colour(tint, min(0.92, strength + 0.25))], [0.0, 0.32, 0.7, 1.0])
                c.drawPaint(skia.Paint(Shader=shade))
        return self.world.makeImageSnapshot()

    def world_image(self, t):
        f = self.film
        passes = int(clamp(math.ceil(f.screen_speed(t) / 12.0), 1, 8))      # motion blur for fast moves
        if passes == 1:
            return self.draw_world(t)
        with self.blend as c:
            c.clear(skia.ColorBLACK)
            for i in range(passes):
                c.drawImage(self.draw_world(t + (i / passes - 0.5) * 0.5 / f.fps), 0, 0, NEAREST, skia.Paint(Alphaf=1.0 / (i + 1)))
        return self.blend.makeImageSnapshot()

    def _fade(self, t):
        f, k = self.film, 1.0
        if f.fade_in > 0 and t < f.fade_in:
            k *= ease_in_out(t / f.fade_in)
        if f.fade_out > 0 and t > f.duration - f.fade_out:
            k *= 1.0 - ease_in_out((t - f.duration + f.fade_out) / f.fade_out)
        return k

    def frame(self, n):
        f = self.film
        t, look = n / f.fps, f.look
        picture = self.world_image(t)
        glow = float(look.get("glow", 0.0))
        if glow > 0:
            with self.tiny as s:
                s.clear(skia.ColorBLACK)
                s.drawImageRect(picture, skia.Rect.MakeWH(self.tw, self.th), SMOOTH, skia.Paint(ColorFilter=self.bright_pass))
            with self.tiny_blur as s:
                s.clear(skia.ColorBLACK)
                s.drawImage(self.tiny.makeImageSnapshot(), 0, 0, NEAREST, self.soften)
        with self.final as c:
            c.saveLayer(None, self.tone)
            c.drawImage(picture, 0, 0, NEAREST)
            if glow > 0:
                c.drawImageRect(self.tiny_blur.makeImageSnapshot(), skia.Rect.MakeWH(self.W, self.H), SMOOTH,
                                skia.Paint(BlendMode=skia.BlendMode.kPlus, Alphaf=min(1.0, glow)))
            c.restore()
            c.drawImage(self.vignette, 0, 0, NEAREST, skia.Paint(BlendMode=skia.BlendMode.kModulate))
            fade = self._fade(t)
            if fade < 0.999:
                c.drawPaint(fill((0, 0, 0), 1 - fade))
            grain = float(look.get("grain", 0.0)) * 6.4
            if grain > 0:
                c.drawImage(self.grain[(n // 2) % len(self.grain)], 0, 0, NEAREST,
                            skia.Paint(BlendMode=skia.BlendMode.kOverlay, Alphaf=min(1.0, grain)))
            if f.overlays:
                unit = min(self.W, self.H) / 1080.0
                self.res.overlay_size = (self.W / unit, self.H / unit)
                c.save()
                c.scale(unit, unit)
                for ov in f.overlays:
                    if ov.visible(t):
                        ov.draw(c, self.res, t)
                c.restore()
        return self.final.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)

    def frame_rgb(self, n):
        return np.ascontiguousarray(self.frame(n)[..., :3])

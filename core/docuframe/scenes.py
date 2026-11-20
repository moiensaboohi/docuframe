"""Build a Film from data: film.json (beats) + a style + the voiceover timing.

An agent writes film.json, never drawing code. Each beat names a scene from the library, the
narration line it belongs to, and optionally the spoken word it lands on. The layout pass places
every beat's cluster in one designed world (style camera "world": one continuous camera glides
between them) or far apart with hard cuts (style camera "cuts").

film.json
{
  "style": "evidence-board",            # a style pack name
  "format": "16:9",                     # 16:9 | 9:16 | 1:1 (also set by docuframe render --format)
  "lang": "en",
  "beats": [
    {"line": 1, "scene": "title", "text": "Twelve Seconds", "sub": "Kitty Hawk, 1903"},
    {"line": 2, "scene": "photo", "photo": "P01", "label": "ORVILLE WRIGHT", "at": "Orville",
     "mark": {"kind": "ellipse", "fx": 0.5, "fy": 0.35, "at": "flew"}},
    {"line": 3, "scene": "big-number", "value": 12, "suffix": " s", "caption": "FIRST FLIGHT", "at": "twelve",
     "source": "Smithsonian NASM"},
    ...
  ]
}

Scene kinds: title, chapter, photo, document, quote, big-number, timeline, comparison, list,
map (needs docuframe map output), lower-third, end. Every beat may carry "source" (shown on screen
while the beat is up) and "hold" (seconds to stay on it before the camera moves on).
"""
from __future__ import annotations

import json
import math
import pathlib

import skia

from . import engine as E
from . import styles as S

FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}
CLUSTER_W, CLUSTER_H = 3600, 2300


# ---------------------------------------------------------------- new items (world space)
class Panel(E.Item):
    """A flat panel (card, quote slip, comparison column) in the style's paper colour."""
    z = 11

    def __init__(self, x, y, w, h, t_in, rgb, rot=0.0, radius=28, shadow=0.35, accent=None, t_out=None):
        super().__init__(t_in, t_out)
        self.x, self.y, self.w, self.h, self.rgb, self.rot, self.radius, self.shadow, self.accent = x, y, w, h, rgb, rot, radius, shadow, accent

    def bounds(self, res):
        r = max(self.w, self.h) * 0.75 + 200
        return skia.Rect.MakeLTRB(self.x - r, self.y - r, self.x + r, self.y + r)

    def cues(self):
        return [("paper", self.t_in, 0.5, {})]

    def draw(self, c, res, t):
        u = E.ease_out_cubic(E.ramp(t, self.t_in, 0.55))
        a = self.fade(t) * u
        if a <= 0:
            return
        c.save(); c.translate(self.x, self.y + (1 - u) * 120); c.rotate(self.rot)
        r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-self.w / 2, -self.h / 2, self.w, self.h), self.radius, self.radius)
        if self.shadow:
            sh = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-self.w / 2 + 30, -self.h / 2 + 50, self.w, self.h), self.radius, self.radius)
            c.drawRRect(sh, E.paint((0, 0, 0), self.shadow * a, blur=60))
        c.drawRRect(r, E.paint(self.rgb, a))
        if self.accent:
            c.drawRect(skia.Rect.MakeXYWH(-self.w / 2, -self.h / 2, 26, self.h), E.paint(self.accent, a))
        c.restore()


class TextBlock(E.Item):
    """Wrapped, shaped text (any script) that fades and rises in. align: left | center | right
    (for right-to-left text, left/right follow reading direction automatically via `start`)."""
    z = 60

    def __init__(self, text, x, y, w, size, t_in, role="serif", rgb=(30, 30, 30), align="center", rot=0.0, t_out=None, dur=0.5):
        super().__init__(t_in, t_out)
        from .fonts import is_rtl
        if align == "start":
            align = "right" if is_rtl(text) else "left"
        self.text, self.x, self.y, self.w, self.size, self.role, self.rgb, self.align, self.rot, self.dur = \
            text, x, y, w, size, role, rgb, align, rot, dur

    def height(self, res):
        return res.book.paragraph(self.text, self.size, self.role, self.rgb, width=self.w, align=self.align).Height

    def bounds(self, res):
        return skia.Rect.MakeLTRB(self.x - self.w, self.y - self.size * 8, self.x + self.w, self.y + self.size * 12)

    def draw(self, c, res, t):
        u = E.ease_out_cubic(E.ramp(t, self.t_in, self.dur))
        a = self.fade(t) * u
        if a <= 0:
            return
        p = res.book.paragraph(self.text, self.size, self.role, self.rgb, width=self.w, align=self.align)
        c.save(); c.translate(self.x, self.y + (1 - u) * self.size * 0.4); c.rotate(self.rot)
        if a < 0.999:
            c.saveLayerAlpha(skia.Rect.MakeXYWH(-self.w / 2 - 50, -50, self.w + 100, p.Height + 100), int(255 * a))
        p.paint(c, -self.w / 2, 0)
        if a < 0.999:
            c.restore()
        c.restore()


class Timeline(E.Item):
    """A horizontal timeline whose events tick on one by one at their own times."""
    z = 40

    def __init__(self, x, y, w, events, times, rgb, accent, t_in, size=120):
        super().__init__(t_in)
        self.x, self.y, self.w, self.events, self.times, self.rgb, self.accent, self.size = x, y, w, events, times, rgb, accent, size

    def bounds(self, res):
        return skia.Rect.MakeLTRB(self.x - self.w, self.y - 1500, self.x + self.w, self.y + 1500)

    def cues(self):
        return [("tick", t, 0.5, {}) for t in self.times]

    def draw(self, c, res, t):
        u = E.ease_out_cubic(E.ramp(t, self.t_in, 0.8))
        if u <= 0:
            return
        x0 = self.x - self.w / 2
        c.drawLine(x0, self.y, x0 + self.w * u, self.y, E.paint(self.rgb, 0.9, stroke=14))
        n = len(self.events)
        for i, (ev, te) in enumerate(zip(self.events, self.times)):
            k = E.ease_out_back(E.ramp(t, te, 0.45))
            if k <= 0:
                continue
            ex = x0 + self.w * (i + 0.5) / n
            up = -1 if i % 2 == 0 else 1
            c.drawCircle(ex, self.y, 34 * k, E.paint(self.accent, 1))
            c.drawLine(ex, self.y, ex, self.y + up * 260 * k, E.paint(self.rgb, 0.8, stroke=8))
            ya = self.y + up * (330 if up < 0 else 420)
            E.draw_text(c, res, str(ev.get("when", "")), ex, ya - (0 if up < 0 else 0), self.size * 1.25, "cond", self.accent, min(1, k), 0.03, "center")
            if ev.get("label"):
                lp = res.book.paragraph(ev["label"], self.size * 0.62, "label", self.rgb, width=self.w / n * 0.92, align="center")
                c.save()
                if k < 1:
                    c.saveLayerAlpha(None, int(255 * min(1, k)))
                lp.paint(c, ex - self.w / n * 0.46, ya + (40 if up < 0 else 40) - (lp.Height + 200 if up < 0 else 0) + (0 if up < 0 else 0))
                if k < 1:
                    c.restore()
                c.restore()


# ---------------------------------------------------------------- overlays (screen space, short side = 1080)
class SourceLine(E.Item):
    """Small "Source: ..." line in the lower corner while a beat is on screen."""
    z = 200

    def __init__(self, text, t_in, t_out, rgb=(240, 236, 228), safe=(60, 60)):
        super().__init__(t_in, t_out)
        self.text, self.rgb, self.safe = text, rgb, safe

    def draw(self, c, res, t):
        a = E.ramp(t, self.t_in + 0.3, 0.4) * self.fade(t)
        if a <= 0:
            return
        W, H = res.overlay_size
        vertical = H > W
        y = H - (H * 0.24 if vertical else self.safe[1])
        x = W - self.safe[0] if not vertical else W / 2
        c.drawRect(skia.Rect.MakeLTRB(0, y - 40, W, H), E.paint((0, 0, 0), 0.0))
        E.draw_text(c, res, self.text, x + 1.5, y + 1.5, 26, "label", (0, 0, 0), 0.6 * a, 0.02, "center" if vertical else "right")
        E.draw_text(c, res, self.text, x, y, 26, "label", self.rgb, 0.9 * a, 0.02, "center" if vertical else "right")


class LowerThird(E.Item):
    z = 210

    def __init__(self, name, role, t_in, t_out, bar_rgb, text_rgb=(250, 248, 244)):
        super().__init__(t_in, t_out)
        self.name, self.role, self.bar, self.text_rgb = name, role, bar_rgb, text_rgb

    def draw(self, c, res, t):
        u = E.ease_out_cubic(E.ramp(t, self.t_in, 0.45)) * self.fade(t)
        if u <= 0:
            return
        W, H = res.overlay_size
        vertical = H > W
        x = 80 if not vertical else 70
        y = H - (200 if not vertical else H * 0.30)
        nw = E.text_width(res, self.name, 46, "cond", 0.04) + 60
        c.drawRect(skia.Rect.MakeXYWH(x, y - 58, nw * u, 76), E.paint(self.bar, 0.95))
        if u > 0.6:
            E.draw_text(c, res, self.name, x + 30, y, 46, "cond", self.text_rgb, (u - 0.6) / 0.4, 0.04)
        if self.role:
            rw = E.text_width(res, self.role, 28, "label") + 50
            c.drawRect(skia.Rect.MakeXYWH(x, y + 22, rw * u, 50), E.paint((20, 20, 20), 0.85))
            if u > 0.7:
                E.draw_text(c, res, self.role, x + 25, y + 56, 28, "label", (235, 235, 235), (u - 0.7) / 0.3)


# ---------------------------------------------------------------- layout
def _pos(i, n, st, fmt):
    lay = st["layout"]
    sp = lay["spacing"] * (2.6 if st["camera"] == "cuts" else 1.0)
    row = max(1, int(lay.get("row", 4)))
    if fmt in ("9:16", "4:5"):
        row = 1     # vertical: a column reads better than a row
    col, r = i % row, i // row
    if r % 2:
        col = row - 1 - col
    if row == 1:
        return 0.0, i * sp * 0.85
    return col * sp, r * sp * 0.72


def _jit(i, deg):
    return ((i * 37) % 7 - 3) / 3.0 * deg


class Builder:
    def __init__(self, doc: E.Doc, plan: dict, style: dict, fmt: str):
        self.doc, self.plan, self.st, self.fmt = doc, plan, style, fmt
        self.W, self.H = FORMATS[fmt]
        self.film = E.Film(doc.duration, fps=int(plan.get("fps", 30)), look=dict(style["finish"]))
        self.film.roles = S.roles(style)
        self.film.lang = plan.get("lang") or doc.timing.get("lang")
        self.c = {k: tuple(v) for k, v in style["tokens"]["color"].items()}
        doc._res = E.Res(1.0, doc.prep, doc.dir / "fonts", roles=self.film.roles, lang=self.film.lang)
        self.prints = []         # (beat index, Print) for strings
        self.chapters = []       # (t, title) for YouTube chapters
        self.sources = []        # every source line shown, for the manifest
        self.photos_used = []
        self.marks = []          # (t, label) timing anchors for the timing check

    # -- time
    def t_of(self, beat, key="at"):
        line = beat.get("line")
        at = beat.get(key)
        if line is None:
            return float(beat.get("t", 0.0))
        if isinstance(at, (int, float)):
            return self.doc.L(line) + float(at)
        if isinstance(at, str):
            nth = 0
            if "#" in at:
                at, nth = at.rsplit("#", 1); nth = int(nth)
            t = self.doc.W(line, at, nth)
            self.marks.append((t, at, line))
            return t
        return self.doc.L(line) + 0.05

    def fit(self, text, size, role="cond", track=0.04, frac=0.9):
        """Shrink a size so the text fits the frame width (vertical frames are narrower)."""
        avail = CLUSTER_W * frac * (0.82 if self.H > self.W else 1.0)
        tw = E.text_width(self.doc.res(), text, size, role, track)
        return size * min(1.0, avail / tw) if tw else size

    def zoom_for(self, w=CLUSTER_W, h=CLUSTER_H):
        s = max(self.W, self.H) / 3840.0
        return min(self.W / (s * w), self.H / (s * h))

    # -- build
    def build(self) -> E.Film:
        beats = self.plan["beats"]
        if not beats:
            raise SystemExit("film.json has no beats")
        starts = [self.t_of(b) for b in beats]
        ends = starts[1:] + [self.doc.duration]
        world = self.st["camera"] != "cuts"
        f = self.film
        prev_center = None
        for i, (b, t0, t1) in enumerate(zip(beats, starts, ends)):
            cx, cy = _pos(i, len(beats), self.st, self.fmt)
            rot = _jit(i, self.st["layout"].get("jitter_deg", 0))
            kind = b["scene"]
            fn = getattr(self, "scene_" + kind.replace("-", "_"), None)
            if fn is None:
                raise SystemExit(f"beat {i + 1}: unknown scene {kind!r}. Scenes: " + ", ".join(
                    n[6:].replace("_", "-") for n in dir(self) if n.startswith("scene_")))
            zoom = fn(b, i, cx, cy, rot, t0, t1) or self.zoom_for()
            if b.get("source"):
                self.sources.append(b["source"])
                f.overlay(SourceLine(self.source_text(b["source"]), t0, t1 - 0.4, self.c.get("text", (240, 236, 228))))
            # camera: arrive on the cluster as the beat starts, push in gently while it holds
            if kind == "lower-third":
                continue
            nxt = ends[i] if i + 1 < len(beats) else self.doc.duration
            last = i == len(beats) - 1
            if world:
                arrive = 0.0 if i == 0 else max(0.0, t0 - 0.05)
                hold = (min(nxt - 0.85, self._pull_t(starts) - 0.3) if last and self._wants_pull(beats, starts) else nxt - 0.85)
                push = 1.03 if self.H > self.W else 1.05
                f.shot(arrive, cx, cy, zoom * 0.97, rot=rot * 0.15)
                if hold > arrive + 0.4:
                    # same point, slow push-in: equal positions give the spline a zero slope, so the
                    # camera settles on the cluster instead of sliding through it
                    f.shot(hold, cx, cy, zoom * push, rot=-rot * 0.1)
            else:
                if i:
                    f.cut(t0 - 0.02)
                f.shot(max(0.0, t0 - 0.02), cx, cy, zoom * 0.98)
                f.shot(max(t0 + 0.3, nxt - 0.06), cx, cy, zoom * 1.08)
            prev_center = (cx, cy)
        # strings between photos (evidence style) and a final pull-back over the whole world
        if self.st["scenes"].get("photo", {}).get("strings") and len(self.prints) > 1:
            for (ia, pa), (ib, pb) in zip(self.prints, self.prints[1:]):
                f.add(E.StringLine((pa.x, pa.y - 600), (pb.x, pb.y - 600), pb.t_in + 0.2, dur=0.9))
        if world and self._wants_pull(beats, starts):
            xs = [_pos(i, len(beats), self.st, self.fmt)[0] for i in range(len(beats))]
            ys = [_pos(i, len(beats), self.st, self.fmt)[1] for i in range(len(beats))]
            mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            span_w, span_h = max(xs) - min(xs) + CLUSTER_W * 1.3, max(ys) - min(ys) + CLUSTER_H * 1.3
            z = self.zoom_for(span_w, span_h)
            tp = self._pull_t(starts)
            f.shot(tp + 1.6, mx, my, z, radius=60000, strength=0.05)
            f.shot(self.doc.duration, mx, my, z * 0.96, radius=60000, strength=0.05)
        return f

    SOURCE_WORD = {"en": "Source", "fa": "منبع", "ar": "المصدر", "ur": "ماخذ", "he": "מקור", "hi": "स्रोत", "bn": "সূত্র",
                   "ta": "ஆதாரம்", "es": "Fuente", "fr": "Source", "pt": "Fonte", "de": "Quelle", "it": "Fonte",
                   "zh": "来源", "ja": "出典", "ko": "출처", "tr": "Kaynak", "ru": "Источник"}

    def source_text(self, src):
        """Source line in the film's language; a source that already says what it is is kept as is."""
        src = str(src)
        low = src.lower()
        if low.startswith(("source", "photo", "©", "data")) or ":" in src[:12]:
            return src
        lang = (self.film.lang or "en").split("-")[0]
        word = self.SOURCE_WORD.get(lang, "Source")
        return f"{word}: {src}"

    def _wants_pull(self, beats, starts):
        """The closing pull-back over the whole world: by default only under an end card, after it
        has been readable for 2.5 s (pulling away from content cuts its reading time)."""
        return (self.st["camera"] != "cuts" and self.plan.get("pullback", beats[-1]["scene"] == "end") and len(beats) > 2
                and self.doc.duration - starts[-1] > 4.5)

    def _pull_t(self, starts):
        return starts[-1] + 2.5

    # -- scenes (each returns the camera zoom it wants, or None for the default)
    def scene_title(self, b, i, cx, cy, rot, t0, t1):
        sc = self.st["scenes"].get("title", {})
        size = b.get("size", sc.get("size", 560))
        size = self.fit(b["text"], size)          # fit the frame: shrink rather than crop
        bar = self.c.get(sc["bar"]) if sc.get("bar") else None
        self.film.add(E.BigText(b["text"], cx, cy, size, t0, rgb=self.c.get(sc.get("color", "text"), (246, 243, 236)),
                                type_on=sc.get("type_on", 0.6), grunge=sc.get("grunge", True), bar=bar,
                                bar_h=sc.get("bar_h", 0.92), shadow=sc.get("shadow", True), hit=sc.get("hit", 0.8)))
        if b.get("sub"):
            self.film.add(E.BigText(b["sub"], cx, cy + size * 0.75, size * 0.32, t0 + 0.6, font="label",
                                    rgb=self.c.get("muted", (200, 190, 180)), grunge=False, shadow=False))
        if b.get("chapter", True):
            self.chapters.append((t0, b.get("chapter_title", b["text"])))
        return None

    def scene_chapter(self, b, i, cx, cy, rot, t0, t1):
        n = b.get("number")
        if n is not None:
            self.film.add(E.BigText(f"{int(n):02d}", cx, cy - 520, 300, t0, rgb=self.c.get("accent"), grunge=False, shadow=False))
        self.film.add(E.BigText(b["title"], cx, cy + 120, b.get("size", 380), t0 + 0.2, rgb=self.c.get("text"),
                                type_on=0.5, grunge=self.st["scenes"].get("chapter", {}).get("grunge", False), hit=0.6))
        self.chapters.append((t0, b["title"]))
        return self.zoom_for(CLUSTER_W * 1.1, CLUSTER_H * 1.1)

    def scene_photo(self, b, i, cx, cy, rot, t0, t1):
        sc = self.st["scenes"].get("photo", {})
        key = b["photo"]
        meta = self.doc.meta.get(key)
        if meta is None:
            raise SystemExit(f"beat {i + 1}: photo {key!r} is not prepared. Add it to photos.json and run docuframe assets.")
        w = b.get("w", sc.get("w", 2700))
        if meta["h"] / meta["w"] * w > CLUSTER_H * 1.05:
            w = CLUSTER_H * 1.05 * meta["w"] / meta["h"]
        pr = E.Print(key, cx, cy, w, rot=rot, t_in=t0, label=b.get("label"), label_t=t0 + 0.6 if b.get("label") else None,
                     pin=sc.get("pin", True), border=sc.get("border", 0.035), label_rgb=self.c.get("label", (176, 24, 20)))
        self.film.add(pr)
        self.prints.append((i, pr))
        self.photos_used.append(key)
        m = b.get("mark")
        if m:
            x, y = self.doc.on(pr, m.get("fx", 0.5), m.get("fy", 0.5))
            pw, ph = pr.size_from(self.doc.meta)
            tm = self.t_of({"line": b.get("line"), "at": m.get("at")}) if m.get("at") else t0 + 1.0
            self.film.add(E.PenMark(m.get("kind", "ellipse"), x, y, m.get("w", 0.35) * pw, m.get("h", 0.3) * ph, t_in=tm,
                                    rot=rot, rgb=self.c.get("accent", (160, 22, 20)), width=16))
        pw, ph = pr.size_from(self.doc.meta)
        return self.zoom_for(max(pw * 1.3, CLUSTER_W * 0.8), max(ph * (1.6 if b.get("label") else 1.35), CLUSTER_H * 0.8))

    def scene_document(self, b, i, cx, cy, rot, t0, t1):
        if b.get("photo"):
            return self.scene_photo({**b, "label": None}, i, cx, cy, rot, t0, t1)
        w, h = 2400, 3000
        doc = E.PaperDoc(cx, cy, w, h, rot=rot, t_in=t0, header=b.get("header", ()), sentence=b.get("text"),
                         sentence_row=b.get("row", 6), sentence_size=b.get("size", 64))
        self.film.add(doc)
        if b.get("phrase") and b.get("text"):
            tm = self.t_of({"line": b.get("line"), "at": b.get("mark_at")}) if b.get("mark_at") else t0 + 1.2
            for k, ((x, y), pw) in enumerate(doc.phrase_spans(self.doc.res(), b["phrase"])):
                self.film.add(E.PenMark("highlight", x, y, pw * 1.04, 0, t_in=tm + 0.35 * k, width=60, rot=rot))
        return self.zoom_for(w * 1.25, h * 1.15)

    def scene_quote(self, b, i, cx, cy, rot, t0, t1):
        paper = self.c.get("paper", (246, 243, 236))
        ink = self.c.get("ink", (40, 30, 22))
        w, h = 3100, 1900
        from .fonts import is_rtl
        q = b["text"]
        quoted = f"«{q}»" if is_rtl(q) else f"“{q}”"
        size = b.get("size", 170)
        res = self.doc.res()
        qh = res.book.paragraph(quoted, size, "serif", ink, width=w * 0.84, align="center").Height
        who = " — ".join(x for x in (b.get("who"), b.get("when")) if x)
        gap, wsize = 110, 105
        total = qh + (gap + wsize * 1.3 if who else 0)
        h = max(h, total + 500)
        self.film.add(Panel(cx, cy, w, h, t0, paper, rot=rot * 0.5, accent=self.c.get("accent")))
        top = cy - total / 2
        self.film.add(TextBlock(quoted, cx, top, w * 0.84, size, t0 + 0.25, role="serif", rgb=ink, align="center"))
        if who:
            self.film.add(TextBlock(who, cx, top + qh + gap, w * 0.8, wsize, t0 + 0.9, role="label", rgb=ink, align="center"))
        return self.zoom_for(w * 1.15, h * 1.15)

    def scene_big_number(self, b, i, cx, cy, rot, t0, t1):
        v = b["value"]
        if isinstance(v, str):
            self.film.add(E.BigText(v, cx, cy, self.fit(v, b.get("size", 900)), t0, rgb=self.c.get("highlight"), hit=0.9))
        else:
            self.film.add(E.Counter(cx, cy + 200, b.get("size", 900), v, t0, dur=b.get("dur", 1.3), prefix=b.get("prefix", ""),
                                    suffix=b.get("suffix", ""), caption=b.get("caption"), rgb=self.c.get("highlight", (246, 206, 46))))
        if b.get("caption") and isinstance(v, str):
            self.film.add(E.BigText(b["caption"], cx, cy + 520, self.fit(b["caption"], 200, "label"), t0 + 0.5, font="label",
                                    rgb=self.c.get("text"), grunge=False))
        return None

    def scene_timeline(self, b, i, cx, cy, rot, t0, t1):
        evs = b["events"]
        times = []
        for k, ev in enumerate(evs):
            if ev.get("at") and b.get("line"):
                times.append(self.t_of({"line": ev.get("line", b["line"]), "at": ev["at"]}))
            else:
                times.append(t0 + 0.5 + (t1 - t0 - 1.0) * k / max(1, len(evs)))
        self.film.add(Timeline(cx, cy, CLUSTER_W * 0.95, evs, times, self.c.get("text"), self.c.get("highlight"), t0))
        return None

    def scene_comparison(self, b, i, cx, cy, rot, t0, t1):
        paper, ink = self.c.get("paper"), self.c.get("ink")
        tall = self.H > self.W
        pw, ph = (3000, 1150) if tall else (1700, 1500)
        for k, side in enumerate((b["left"], b["right"])):
            x, y = (cx, cy + (k - 0.5) * (ph + 160)) if tall else (cx + (k - 0.5) * (pw + 160), cy)
            tk = t0 + 0.1 + k * 0.6
            self.film.add(Panel(x, y, pw, ph, tk, paper, accent=self.c.get("accent") if k else self.c.get("muted")))
            ts = self.fit(side["title"], 260, "cond", frac=pw / CLUSTER_W * 0.85)
            body = "\n".join(side.get("lines", []))
            bh = self.doc.res().book.paragraph(body, 140, "label", ink, width=pw * 0.85, align="center").Height if body else 0
            top = y - (ts * 1.25 + (60 + bh if body else 0)) / 2
            self.film.add(TextBlock(side["title"], x, top, pw * 0.9, ts, tk + 0.2, role="cond", rgb=ink))
            if body:
                self.film.add(TextBlock(body, x, top + ts * 1.25 + 60, pw * 0.85, 140, tk + 0.4, role="label", rgb=ink))
        return self.zoom_for(CLUSTER_W * 1.05, (2 * ph + 400) if tall else CLUSTER_H)

    def scene_list(self, b, i, cx, cy, rot, t0, t1):
        paper, ink = self.c.get("paper"), self.c.get("ink")
        items = b["items"]
        row = 300
        h = 520 + row * len(items) + (260 if b.get("title") else 0)
        w = 3100
        self.film.add(Panel(cx, cy, w, h, t0, paper, rot=rot * 0.4, accent=self.c.get("accent")))
        y = cy - h / 2 + 230
        if b.get("title"):
            self.film.add(TextBlock(b["title"], cx, y, w * 0.86, 200, t0 + 0.2, role="cond", rgb=ink, align="start"))
            y += 330
        for k, it in enumerate(items):
            tk = self.t_of({"line": b.get("line"), "at": it.get("at")}) if isinstance(it, dict) and it.get("at") else t0 + 0.6 + k * 0.7
            txt = it["text"] if isinstance(it, dict) else it
            self.film.add(TextBlock(f"{k + 1}. {txt}" if b.get("numbered", True) else txt, cx, y + k * row, w * 0.86, 150, tk,
                                    role="label", rgb=ink, align="start"))
        return self.zoom_for(w * 1.15, h * 1.2)

    def scene_map(self, b, i, cx, cy, rot, t0, t1):
        data = self.doc.map(b["map"])
        K = b.get("scale", 9000)
        gm = E.GeoMap(data, K, origin=(cx - K * (data["frame"][0] + data["frame"][2]) / 2 if data.get("frame") else cx,
                                       cy - K * (data["frame"][1] + data["frame"][3]) / 2 if data.get("frame") else cy),
                      look=self.st.get("map_look", "explainer"), t_in=t0 - 0.5)
        self.film.add(gm)
        if b.get("fill"):
            self.film.add(E.RegionFill(gm, b["fill"], self.c.get("accent"), t0 + 0.6))
        return None

    def scene_lower_third(self, b, i, cx, cy, rot, t0, t1):
        self.film.overlay(LowerThird(b["name"], b.get("role", ""), t0, b.get("until", t0 + 5.0), self.c.get("label", (176, 24, 20))))
        return None

    def scene_end(self, b, i, cx, cy, rot, t0, t1):
        self.film.add(E.BigText(b.get("text", ""), cx, cy - 200, b.get("size", 420), t0, rgb=self.c.get("text"), type_on=0.6, hit=0.5))
        if b.get("sub"):
            self.film.add(TextBlock(b["sub"], cx, cy + 250, 3000, 130, t0 + 0.8, role="label", rgb=self.c.get("text")))
        return None


def load_plan(proj: pathlib.Path) -> dict:
    p = proj / "film.json"
    if not p.exists():
        raise SystemExit(f"{p} not found. Write the beat plan (see templates/ for worked examples).")
    return json.loads(p.read_text(encoding="utf-8"))


def channel_file(proj: pathlib.Path) -> dict | None:
    for p in (proj / "channel.json", proj.parent / "channel.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


def build(proj: pathlib.Path, fmt: str | None = None):
    """(film, builder) for a project folder."""
    proj = pathlib.Path(proj).resolve()
    plan = load_plan(proj)
    style = S.load(plan.get("style", "evidence-board"), proj, channel_file(proj))
    fmt = fmt or plan.get("format", "16:9")
    doc = E.Doc(proj)
    from .assets import textures
    textures(doc.prep, extra=[style['finish']['board']])
    b = Builder(doc, plan, style, fmt)
    film = b.build()
    return film, b, doc, style

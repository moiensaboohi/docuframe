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
from . import skins as K
from . import styles as S
from .layouts import EditorialScenes

FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}
CLUSTER_W, CLUSTER_H = 3600, 2300


# ---------------------------------------------------------------- new items (world space)
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


class Builder(EditorialScenes):
    def __init__(self, doc: E.Doc, plan: dict, style: dict, fmt: str):
        self.doc, self.plan, self.st, self.fmt = doc, plan, style, fmt
        self.W, self.H = FORMATS[fmt]
        self.skin = {**S.DEFAULTS["skin"], **style.get("skin", {})}
        look = dict(style["finish"])
        ground = style.get("ground", {})
        if ground.get("kind", "texture") != "texture":
            look["board"] = None
            look["bg"] = tuple(ground.get("color", look.get("bg", (20, 20, 20))))
            if ground.get("kind") == "gradient":
                look["bg2"] = tuple(ground.get("color2", look["bg"]))
        look["handheld"] = style.get("camera_feel", {}).get("handheld", 1.0)
        self.film = E.Film(doc.duration, fps=int(plan.get("fps", 30)), look=look)
        if ground.get("pattern"):
            self.film.add(K.Ground(ground["pattern"], ground.get("pattern_rgb", (0, 0, 0)), ground.get("pattern_alpha", 0.08),
                                   ground.get("pattern_step", 240)))
        if self.skin.get("letterbox") and self.W > self.H:
            self.film.overlay(K.Letterbox(doc.duration))
        self.feel = {"travel": 0.85, "push": 1.05, **style.get("camera_feel", {})}
        self.film.roles = S.roles(style)
        self.film.lang = plan.get("lang") or doc.timing.get("lang")
        self.c = {k: tuple(v) for k, v in style["tokens"]["color"].items()}
        doc._res = E.Res(1.0, doc.prep, doc.dir / "fonts", roles=self.film.roles, lang=self.film.lang)
        self.prints = []         # (beat index, Print) for strings
        self.chapters = []       # (t, title) for YouTube chapters
        self.sources = []        # every source line shown, for the manifest
        self.photos_used = []
        self.marks = []          # (t, label) timing anchors for the timing check
        self.ed_init()

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
        # a beat lasts until the next beat that takes the screen; overlays (lower thirds) don't
        ends = []
        for k in range(len(beats)):
            nxt = [starts[j] for j in range(k + 1, len(beats)) if beats[j]["scene"] != "lower-third"]
            ends.append(nxt[0] if nxt else self.doc.duration)
        world = self.st["camera"] != "cuts"
        f = self.film
        prev_center = None
        for i, (b, t0, t1) in enumerate(zip(beats, starts, ends)):
            cx, cy = _pos(i, len(beats), self.st, self.fmt)
            rot = _jit(i, self.st["layout"].get("jitter_deg", 0))
            kind = b["scene"]
            fn = getattr(self, "scene_" + kind.replace("-", "_"), None)
            if self.layout != "center":
                fn = getattr(self, "ed_" + kind.replace("-", "_"), None) or fn
            if fn is None:
                raise SystemExit(f"beat {i + 1}: unknown scene {kind!r}. Scenes: " + ", ".join(
                    n[6:].replace("_", "-") for n in dir(self) if n.startswith("scene_")))
            zoom = fn(b, i, cx, cy, rot, t0, t1) or self.zoom_for()
            if b.get("source"):
                self.sources.append(b["source"])
                f.overlay(K.SourceTag(self.source_text(b["source"]), t0, t1 - 0.4, self.skin["source"],
                                      self.c.get("source_fg", self.c.get("text")), self.c.get("source_bg", self.c.get("ink")),
                                      bool(self.skin.get("letterbox"))))
            self.decorate(b, i, cx, cy, t0)
            # camera: arrive on the cluster as the beat starts, push in gently while it holds
            if kind == "lower-third":
                continue
            nxt = ends[i] if i + 1 < len(beats) else self.doc.duration
            last = i == len(beats) - 1
            if world:
                travel = self.feel["travel"]
                arrive = 0.0 if i == 0 else max(0.0, t0 - 0.05)
                hold = (min(nxt - travel, self._pull_t(starts) - 0.3) if last and self._wants_pull(beats, starts) else nxt - travel)
                push = 1 + (self.feel["push"] - 1) * (0.6 if self.H > self.W else 1.0)
                f.shot(arrive, cx, cy, zoom * 0.97, rot=rot * 0.15)
                if hold > arrive + 0.4:
                    # same point, slow push-in: equal positions give the spline a zero slope, so the
                    # camera settles on the cluster instead of sliding through it
                    f.shot(hold, cx, cy, zoom * push, rot=-rot * 0.1)
            else:
                if i:
                    f.cut(t0 - 0.02)
                f.shot(max(0.0, t0 - 0.02), cx, cy, zoom * 0.98)
                f.shot(max(t0 + 0.3, nxt - 0.06), cx, cy, zoom * self.feel["push"])
            prev_center = (cx, cy)
        # strings between photos (evidence style) and a final pull-back over the whole world
        if self.skin.get("strings") and len(self.prints) > 1:
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
    # -- shared pieces
    def headline(self, text, x, y, size, t0, role="display", rgb=None, kicker=None, accent_rule=True):
        """A title in the style's title skin. Returns the size actually used."""
        kind = self.skin["title"]
        rgb = rgb or self.c.get("text")
        size = self.fit(text, size, role, 0.04 if kind == "bar" else 0.0)
        f = self.film
        if kind == "kinetic" or kind == "stack":
            if kicker and kind == "stack":
                f.add(K.Kicker(kicker, x, y - size * 1.3, max(72, size * 0.26), t0, self.c.get("accent"), self.c.get("on_accent", (255, 255, 255)),
                               self.skin["motion"]))
            f.add(K.Kinetic(text, x, y, size, t0 + (0.15 if kicker else 0), rgb, role, self.c.get("accent"), accent_rule and kind == "kinetic"))
        elif kind == "serif":
            f.add(E.BigText(text, x, y, size, t0, font=role, rgb=rgb, track=0.01, grunge=False, shadow=False, hit=None))
            f.add(K.Rule(x, y - size * 0.32, E.text_width(self.doc.res(), text, size, role, 0.01) / 2 + size * 0.5, size * 1.2, t0 + 0.3,
                         self.c.get("accent", rgb), max(4, size * 0.012)))
        elif kind == "torn":
            w = E.text_width(self.doc.res(), text, size, role, 0.02) + size * 1.4
            f.add(K.Card(x, y - size * 0.36, w, size * 1.55, t0, self.c.get("paper"), "torn", "slap", rot=-1.5, seed=len(text)))
            f.add(E.BigText(text, x, y, size, t0 + 0.12, font=role, rgb=self.c.get("ink"), track=0.02, grunge=False, shadow=False, hit=0.6))
        else:   # bar
            sc = self.st["scenes"].get("title", {})
            bar = self.c.get(sc.get("bar", "label"))
            f.add(E.BigText(text, x, y, size, t0, font=role, rgb=rgb, type_on=sc.get("type_on", 0.6), grunge=sc.get("grunge", True), bar=bar,
                            bar_h=sc.get("bar_h", 0.92), shadow=sc.get("shadow", True), hit=sc.get("hit", 0.8)))
        return size

    def panel(self, x, y, w, h, t0, rot=0.0, accent=None, seed=1):
        return self.film.add(K.Card(x, y, w, h, t0, self.c.get("paper"), self.skin["panel"], self.skin["motion"], rot=rot,
                                    accent=accent, ink=self.c.get("ink"), seed=seed))

    def decorate(self, b, i, cx, cy, t0):
        kind = self.skin.get("accents", "none")
        if kind == "backdrop":      # the film's own photos behind glass; quiet light if the film has none
            keys = [k for k in self.doc.meta]
            w = getattr(self, "vis_w", CLUSTER_W) * 1.2
            h = getattr(self, "vis_h", CLUSTER_H) * 1.2
            if keys:
                key = b.get("photo") if b.get("photo") in self.doc.meta else keys[i % len(keys)]
                self.film.add(K.Backdrop(key, cx, cy, w, h, self.c.get("bg", (0, 0, 0)), self.st.get("backdrop_wash", 0.55),
                                         self.st.get("backdrop_blur", 0.0) * getattr(self, "px", 1.0)))
                return
            kind = "blobs"
        if kind == "blobs":         # colour light behind glass, on every beat so the camera never leaves it
            pal = [self.c[k] for k in ("blob1", "blob2", "blob3", "blob4") if k in self.c] or \
                  [self.c.get(k) for k in ("accent", "highlight", "label") if self.c.get(k)]
            w = getattr(self, "vis_w", CLUSTER_W) * 1.25
            h = getattr(self, "vis_h", CLUSTER_H) * 1.25
            self.film.add(K.Blobs(cx, cy, w, h, pal, seed=i, alpha=self.st.get("blob_alpha", 0.85)))
            return
        if self.layout != "center":
            return
        if kind == "none" or b["scene"] in ("lower-third", "map", "photo") and kind != "corners":
            return
        if kind in ("shapes", "scraps", "halftone") and i % 2:      # every other beat: variety, not clutter
            return
        palette = [self.c.get(k) for k in ("accent", "highlight", "label", "muted") if self.c.get(k)]
        if kind == "halftone":
            palette = [self.c.get("highlight", self.c.get("accent"))]
        if kind == "corners":
            palette = [self.c.get("accent")]
        self.film.add(K.Accents(kind, cx, cy, CLUSTER_W * 0.92, CLUSTER_H * 0.92, t0 + 0.1, palette, seed=i + 3))

    # -- scenes (each returns the camera zoom it wants, or None for the default)
    def scene_title(self, b, i, cx, cy, rot, t0, t1):
        size = self.headline(b["text"], cx, cy, b.get("size", self.st["scenes"].get("title", {}).get("size", 560)), t0,
                             kicker=b.get("kicker") or (b.get("sub") if self.skin["title"] == "stack" else None))
        if b.get("sub") and self.skin["title"] != "stack":
            self.film.add(TextBlock(b["sub"], cx, cy + size * 0.55, CLUSTER_W * 0.8, max(110, size * 0.24), t0 + 0.6, role="label",
                                    rgb=self.c.get("muted", self.c.get("text"))))
        if b.get("chapter", True):
            self.chapters.append((t0, b.get("chapter_title", b["text"])))
        return None

    def scene_chapter(self, b, i, cx, cy, rot, t0, t1):
        n = b.get("number")
        kick = b.get("kicker") or (f"{self.chapter_word()} {int(n):02d}" if n is not None else None)
        if kick and self.skin["title"] != "stack":
            self.film.add(K.Kicker(kick, cx, cy - 560, 70, t0, self.c.get("accent"), self.c.get("on_accent", (255, 255, 255)), self.skin["motion"]))
        self.headline(b["title"], cx, cy + 80, b.get("size", 420), t0 + 0.15, kicker=kick)
        self.chapters.append((t0, b["title"]))
        return self.zoom_for(CLUSTER_W * 1.1, CLUSTER_H * 1.1)

    def chapter_word(self):
        return {"fa": "فصل", "ar": "الفصل", "hi": "अध्याय", "es": "CAPÍTULO", "fr": "CHAPITRE", "de": "KAPITEL", "pt": "CAPÍTULO",
                "zh": "第", "ja": "第"}.get((self.film.lang or "en").split("-")[0], "CHAPTER")

    def scene_photo(self, b, i, cx, cy, rot, t0, t1):
        sc = self.st["scenes"].get("photo", {})
        key = b["photo"]
        meta = self.doc.meta.get(key)
        if meta is None:
            raise SystemExit(f"beat {i + 1}: photo {key!r} is not prepared. Add it to photos.json and run docuframe assets.")
        skin = b.get("skin", self.skin["photo"])
        w = b.get("w", sc.get("w", 3300 if skin == "full" else 2700))
        limit = CLUSTER_H * (1.1 if skin == "full" else 1.0)
        if meta["h"] / meta["w"] * w > limit:
            w = limit * meta["w"] / meta["h"]
        label = b.get("label")
        pr = K.Photo(key, cx, cy, w, t0, skin=skin, motion=self.skin["motion"], rot=rot if skin != "full" else 0.0, label=label,
                     label_t=t0 + 0.6 if label else None, caption=b.get("caption"), bar_rgb=self.c.get("label", (176, 24, 20)),
                     ink=self.c.get("ink"), paper=self.c.get("photo_paper", (250, 248, 242)), seed=i + 1)
        self.film.add(pr)
        self.prints.append((i, pr))
        self.photos_used.append(key)
        m = b.get("mark")
        pw, ph = pr.size(self.doc.meta)
        if m:
            x, y = E.turn(pr.x, pr.y, (m.get("fx", 0.5) - 0.5) * pw, (m.get("fy", 0.5) - 0.5) * ph, pr.rot)
            tm = self.t_of({"line": b.get("line"), "at": m.get("at")}) if m.get("at") else t0 + 1.0
            self.film.add(E.PenMark(m.get("kind", "ellipse"), x, y, m.get("w", 0.35) * pw, m.get("h", 0.3) * ph, t_in=tm,
                                    rot=pr.rot, rgb=self.c.get("mark", self.c.get("accent", (160, 22, 20))), width=16))
        if self.skin.get("accents") == "corners":
            self.film.add(K.Accents("corners", cx, cy, pw * 1.12, ph * 1.12, t0 + 0.3, [self.c.get("accent")]))
        if skin == "full":
            return self.zoom_for(pw * 1.02, ph * 1.02)
        if skin == "polaroid":
            ph += pw * 0.22         # the white foot hangs under the picture
        return self.zoom_for(max(pw * 1.3, CLUSTER_W * 0.8), max(ph * (1.6 if label else 1.35), CLUSTER_H * 0.8))

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
        qh = res.book.paragraph(quoted, size, self.skin.get("quote_font", "serif"), ink, width=w * 0.84, align="center").Height
        who = " — ".join(x for x in (b.get("who"), b.get("when")) if x)
        gap, wsize = 110, 105
        total = qh + (gap + wsize * 1.3 if who else 0)
        h = max(h, total + 500)
        self.panel(cx, cy, w, h, t0, rot=rot * 0.5, accent=self.c.get("accent"), seed=i)
        top = cy - total / 2
        self.film.add(TextBlock(quoted, cx, top, w * 0.84, size, t0 + 0.25, role=self.skin.get("quote_font", "serif"), rgb=ink, align="center"))
        if who:
            self.film.add(TextBlock(who, cx, top + qh + gap, w * 0.8, wsize, t0 + 0.9, role="label", rgb=ink, align="center"))
        return self.zoom_for(w * 1.15, h * 1.15)

    def scene_big_number(self, b, i, cx, cy, rot, t0, t1):
        v = b["value"]
        col = self.c.get("number", self.c.get("highlight"))
        kind = self.skin["number"]
        role = self.skin.get("number_font", "cond")
        shadow = self.skin.get("shadow", 0.45)
        shadow_rgb = self.c.get("shadow", (0, 0, 0))
        cap_rgb = self.c.get(self.skin.get("caption_color", "number"), col)
        size = b.get("size", 900 if kind == "counter" else 760)
        if isinstance(v, str):
            size = self.fit(v, size, role, 0.02)
            self.film.add(E.BigText(v, cx, cy, size, t0, font=role, rgb=col, grunge=self.skin["title"] == "bar", hit=0.9,
                                    shadow=shadow, shadow_rgb=shadow_rgb))
            if b.get("caption"):
                self.film.add(TextBlock(b["caption"], cx, cy + size * 0.22, CLUSTER_W * 0.8, max(130, size * 0.2), t0 + 0.5, role="label",
                                        rgb=self.c.get("text")))
            return None
        share = b.get("share")
        if share is None and b.get("of"):
            share = float(v) / float(b["of"])
        if kind == "ring" and share is None:
            kind = "counter"        # a ring must measure a real share; a full ring around any number is decoration
        dec = None
        frac = repr(float(v)).split(".")[1]
        dec = 0 if frac == "0" else min(3, len(frac))
        final = f"{b.get('prefix', '')}{float(v):,.{dec}f}{b.get('suffix', '')}"
        caption = b.get("caption")
        gap = 0.45
        csize = min(200, max(120, size * 0.2))
        ny = cy + size * 0.22
        if kind == "ring":
            r = size * 0.95
            gy = cy - size * 0.12
            self.film.add(K.Gauge(cx, gy, r, share if share is not None else 1.0, t0, self.c.get("accent"),
                                  self.c.get("muted", (128, 128, 128)), "ring"))
            # the number sits inside the ring; the caption goes under the ring
            size = r * 0.62
            tw = E.text_width(self.doc.res(), final, size, role, 0.02)
            if tw > r * 1.5:
                size *= r * 1.5 / tw
            ny = gy + size * 0.36
            gap = (gy + r + r * 0.3 - ny) / size
        elif kind == "bar":
            size = self.fit(final, size, role, 0.02, 0.8)
            ny = cy + size * 0.22
            tw = E.text_width(self.doc.res(), final, size, role, 0.02)
            self.film.add(K.Gauge(cx, ny + size * 0.16, tw / 2.4, share if share is not None else 1.0, t0 + 0.2, self.c.get("accent"),
                                  self.c.get("muted", (128, 128, 128)), "bar"))
            gap = 0.75
        else:
            size = self.fit(final, size, role, 0.02)
            ny = cy + size * 0.22
        self.film.add(E.Counter(cx, ny, size, v, t0, dur=b.get("dur", 1.3), prefix=b.get("prefix", ""), suffix=b.get("suffix", ""),
                                caption=caption.upper() if caption and self.skin.get("caps_captions", True) else caption,
                                rgb=col, font=role, shadow=shadow, shadow_rgb=shadow_rgb, caption_font="label", caption_rgb=cap_rgb,
                                caption_gap=gap, decimals=dec, caption_size=csize, caption_max=CLUSTER_W * 0.78))
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
            self.panel(x, y, pw, ph, tk, accent=self.c.get("accent") if k else self.c.get("muted"), seed=i * 7 + k)
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
        self.panel(cx, cy, w, h, t0, rot=rot * 0.4, accent=self.c.get("accent"), seed=i)
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
        x0, y0, x1, y1 = data["frame"]
        # fit the map to the frame unless the beat sets a scale
        sk = b.get("scale") or min(getattr(self, "vis_w", CLUSTER_W) * 0.84 / max(1e-6, x1 - x0),
                                  getattr(self, "vis_h", CLUSTER_H) * 0.80 / max(1e-6, y1 - y0))
        gm = E.GeoMap(data, sk, origin=(cx - sk * (x0 + x1) / 2, cy - sk * (y0 + y1) / 2),
                      look=self.st.get("map_look", "explainer"), t_in=t0 - 0.5)
        self.film.add(gm)
        if b.get("fill"):
            self.film.add(E.RegionFill(gm, b["fill"], self.c.get("accent"), t0 + 0.6))
        from .maps import project
        pj = data.get("projection", {"kind": "equirect", "lon0": 0.0})
        for k, pin in enumerate(b.get("pins", [])):
            px, py = gm.w(project(pin["lon"], pin["lat"], pj["kind"], pj["lon0"]))
            tp = self.t_of({"line": b.get("line"), "at": pin["at"]}) if pin.get("at") and b.get("line") else t0 + 1.0 + 0.4 * k
            self.film.add(K.MapPin(px, py, pin.get("label", ""), tp, self.c.get("mark", self.c.get("accent")),
                                   self.c.get("text", (20, 20, 20)), size=getattr(self, "px", 2.0) * 34, side=pin.get("side", 1)))
        for k, rt in enumerate(b.get("routes", [])):
            pts = [gm.w(project(lo, la, pj["kind"], pj["lon0"])) for lo, la in rt["points"]]
            if rt.get("line") or (rt.get("at") is not None and b.get("line")):
                tr = self.t_of({"line": rt.get("line", b.get("line")), "at": rt.get("at", 0.2)})
            else:
                tr = t0 + 0.8 + 1.6 * k
            col = self.c.get(rt.get("color", "accent"), self.c.get("accent"))
            px = getattr(self, "px", 2.0)
            self.film.add(K.PathRoute(pts, tr, rt.get("dur", 2.2), col, px * rt.get("width", 5), rt.get("label"),
                                      self.c.get("text", (20, 20, 20)), px * 26, rt.get("dashed", False),
                                      label_at=rt.get("label_at", 1.0), label_side=rt.get("label_side", 1)))
        return None

    def scene_lower_third(self, b, i, cx, cy, rot, t0, t1):
        self.film.overlay(K.NameTag(b["name"], b.get("role", ""), t0, b.get("until", t0 + 5.0), self.skin["lower_third"],
                                    self.c.get("label", self.c.get("accent")), self.c.get("lt_fg", (250, 248, 244)), self.c.get("lt_panel", (20, 20, 20))))
        return None

    def scene_end(self, b, i, cx, cy, rot, t0, t1):
        size = self.headline(b.get("text", ""), cx, cy - 150, b.get("size", 440), t0)
        if b.get("sub"):
            self.film.add(TextBlock(b["sub"], cx, cy - 150 + size * 0.5, 3000, 130, t0 + 0.8, role="label", rgb=self.c.get("muted", self.c.get("text"))))
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
    from .assets import prep_photos, textures
    if style.get("ground", {}).get("kind", "texture") == "texture":
        textures(doc.prep, extra=[style["finish"]["board"]])
    gfile = doc.prep / "photos" / "grade.txt"
    spec = proj / "photos.json"
    if spec.exists():          # photos follow the style's grade; re-grade when the style changed
        want = json.loads(spec.read_text(encoding="utf-8")).get("grade")
        want = want if want not in (None, "auto") else style.get("photo_grade", "bw")
        if not gfile.exists() or gfile.read_text(encoding="utf-8") != want:
            prep_photos(proj, want)
            doc._meta = None
    b = Builder(doc, plan, style, fmt)
    film = b.build()
    return film, b, doc, style

"""Modern layouts for the scene library: "editorial" and "deck".

The classic layout centres one big element per beat. These layouts compose each beat inside the
frame the camera will show, on a grid with real margins and a type scale measured in output pixels
(at 1080p), so text stays small and calm: an eyebrow, a headline, a supporting line, a number with
a thin meter, a photo with a text column beside it. Alignment is "start" (reading direction, so
right-aligned for RTL) or "center".

  editorial  each beat is a composed frame; optional glass/surface card behind the text ("wrap").
  deck       slide grammar: a header at the top-left with a short accent bar, content in the body
             area below, a page number in the footer; title slides can be a full colour field.

Style data that drives this (all optional):
  skin.layout        editorial | deck
  skin.align         start | center
  skin.panel         none | surface | liquid | fill      (cards behind grouped text)
  skin.wrap          true: put titles/numbers/quotes on a card
  skin.photo         rounded | liquid | plain | frame ...
  skin.title_fill    true: title/chapter/end beats sit on a full-frame accent field
  skin.eyebrow_sub   true: a title's "sub" becomes the small line above it
  skin.number_gradient  [token, token]: gradient number (check flags it as slop; no built-in pack uses it)
  skin.accents       blobs (soft colour light, for glass) | none
  type               {"title": 92, "body": 34, ...}  sizes in px at 1080p (see TYPE)
"""
from __future__ import annotations

from . import engine as E
from . import skins as K
from .fonts import detect_scripts, is_rtl

TYPE = {"eyebrow": 27, "title": 92, "chapter": 80, "end": 72, "slide": 50, "body": 34, "number": 190, "caption": 30,
        "quote": 48, "list": 34, "year": 40, "label": 24, "page": 20}
RTL_LANGS = {"fa", "ar", "ur", "he", "ps", "ku", "sd", "yi"}


class EditorialScenes:
    # ---------------------------------------------------------------- setup
    def ed_init(self):
        self.layout = self.skin.get("layout", "center")
        if self.layout == "center":
            return
        z0 = self.zoom_for()
        s = max(self.W, self.H) / 3840.0
        push = self.feel.get("push", 1.02)
        self.vis_w = self.W / (s * z0 * push)
        self.vis_h = self.H / (s * z0 * push)
        self.tall = self.H > self.W
        self.px = self.vis_w / (1080.0 if self.tall else 1920.0)
        self.mx = self.vis_w * (0.08 if self.tall else 0.085)
        self.my = self.vis_h * (0.075 if self.tall else 0.1)
        self.cw = self.vis_w - 2 * self.mx
        self.ty = {**TYPE, **self.st.get("type", {})}
        self.align = self.skin.get("align", "start")
        self.rtl = (self.film.lang or "en").split("-")[0] in RTL_LANGS
        # neighbours must never peek into a composed frame
        lay = dict(self.st["layout"])
        lay["spacing"] = max(lay.get("spacing", 5000), self.vis_w * 1.35, (self.vis_h * 1.35 / 0.85) if self.tall else 0)
        lay["jitter_deg"] = 0
        self.st = {**self.st, "layout": lay}
        self.page = 0

    def ts(self, name):
        if not self.tall:
            return self.ty[name] * self.px
        # phones: headlines keep their size, small text grows so it stays readable at arm's length
        return self.ty[name] * self.px * (0.95 if name in ("title", "chapter", "end", "number") else 1.3)

    def col(self, key, fallback="text"):
        return self.c.get(key, self.c.get(fallback, (20, 20, 20)))

    # ---------------------------------------------------------------- geometry
    def frame(self, cx, cy):
        """(left, top, right, bottom) of the content area the camera shows for this beat."""
        return cx - self.vis_w / 2 + self.mx, cy - self.vis_h / 2 + self.my, cx + self.vis_w / 2 - self.mx, cy + self.vis_h / 2 - self.my

    def box(self, cx, frac=1.0, align=None):
        align = align or self.align
        w = self.cw * frac
        if align == "center":
            return cx - w / 2, w
        x0 = cx - self.cw / 2
        return (x0 + self.cw - w, w) if self.rtl else (x0, w)

    # ---------------------------------------------------------------- building blocks
    def T(self, text, size, role, rgb, t, gap=0.0, frac=0.8, leading=None, track=0.0, gradient=None, align=None, motion="rise"):
        return {"kind": "type", "text": str(text), "size": size, "role": role, "rgb": rgb, "t": t, "gap": gap, "frac": frac,
                "leading": leading, "track": track, "gradient": gradient, "align": align, "motion": motion}

    def stack(self, rows, cx, cy, box=None):
        """Lay rows top to bottom, centred on cy as a group. box=(x, w) overrides the column.
        Returns (top, bottom, widest line, column x, column w)."""
        res = self.doc.res()
        made = []
        for r in rows:
            if r["kind"] == "meter":
                made.append((r, None, r["thick"]))
                continue
            align = r.get("align") or self.align
            x, w = box if box else self.box(cx, r["frac"], align)
            lead = r["leading"]
            if lead and (is_rtl(r["text"]) or detect_scripts(r["text"]) - {"latin"}):
                lead = max(lead, 1.4)          # joined and Indic scripts need their full line height
            kw = dict(role=r["role"], rgb=r["rgb"], align="center" if align == "center" else ("right" if self.rtl else "left"), motion=r["motion"],
                      gradient=r["gradient"], track=r["track"], leading=lead)
            if r["kind"] == "count":
                it = K.CountType(r["value"], r["prefix"], r["suffix"], r["decimals"], x, 0, w, r["size"], r["t"], **kw)
            else:
                it = K.Type(r["text"], x, 0, w, r["size"], r["t"], **kw)
            made.append((r, it, it.height(res)))
        total = sum(h for _, _, h in made) + sum(r["gap"] for r, _, _ in made[1:])
        top = cy - total / 2
        y = top
        widest = 0.0
        for k, (r, it, h) in enumerate(made):
            if k:
                y += r["gap"]
            if it is None:          # meter
                x, w = box if box else self.box(cx, r["frac"], r.get("align") or self.align)
                if (r.get("align") or self.align) == "center":
                    x, w = cx - r["w"] / 2, r["w"]
                elif self.rtl:
                    x, w = x + w - r["w"], r["w"]
                else:
                    w = r["w"]
                self.film.add(K.Meter(x, y, w, r["share"], r["t"], r["rgb"], self.col("muted"), r["thick"], rtl=self.rtl))
                widest = max(widest, w)
            else:
                it.y = y
                self.film.add(it)
                widest = max(widest, it.line_width(res))
            y += h
        x, w = box if box else self.box(cx, max((r.get("frac", 0.8) for r in rows), default=0.8))
        return top, top + total, widest, x, w

    def surface(self, x, y, w, h, t, radius=None, kind=None):
        kind = kind or self.skin.get("panel", "surface")
        if kind == "none":
            return None
        r = radius if radius is not None else self.px * self.st.get("radius", 28)
        dark = sum(self.col("bg")[:3]) < 300
        return self.film.add(K.Surface(x, y, w, h, t, self.c.get("glass", self.c.get("paper", (255, 255, 255))), r, kind,
                                       stroke=(self.col("muted"), 0.18, max(2.0, self.px * 1.2)) if kind == "surface" and self.skin.get("hairline") else None,
                                       tint_a=self.st.get("glass_alpha", 0.18), dark=dark, blur=self.px * 26,
                                       shadow=0.0 if kind == "surface" and self.skin.get("flat") else (0.18 if dark else 0.08)))

    def wrap(self, top, bottom, widest, x, w, cx, t, pad=None):
        """A card behind a text group (glass or surface)."""
        if not self.skin.get("wrap") or self.skin.get("panel", "none") == "none":
            return
        pad = pad or self.px * 64
        if self.align == "center":
            left, cwid = cx - widest / 2 - pad, widest + 2 * pad
        elif self.rtl:
            left, cwid = x + w - widest - pad, widest + 2 * pad
        else:
            left, cwid = x - pad, widest + 2 * pad
        self.surface(left, top - pad, cwid, bottom - top + 2 * pad, t - 0.05)

    def header(self, text, cx, cy, t):
        """Deck slide header at the top of the frame. Returns the y where the body area starts."""
        l, top, r, b = self.frame(cx, cy)
        size = self.ts("slide")
        x, w = self.box(cx, 0.86, "start")
        it = K.Type(text, x, top, w, size, t, role="display", rgb=self.col("text"), leading=1.1, track=-0.01,
                    align="right" if self.rtl else "left")
        self.film.add(it)
        h = it.height(self.doc.res())
        bw, bh = self.px * 56, self.px * 6
        bx = x + w - bw if self.rtl else x
        self.film.add(K.Surface(bx, top + h + self.px * 22, bw, bh, t + 0.15, self.col("accent"), bh / 2, "fill"))
        return top + h + self.px * 22 + bh + self.px * 40

    def body_center(self, cx, cy, start):
        l, top, r, b = self.frame(cx, cy)
        return (start + b) / 2

    def page_number(self, cx, cy, t):
        self.page += 1
        l, top, r, b = self.frame(cx, cy)
        y = cy + self.vis_h / 2 - self.my * 0.62
        x, w = self.box(cx, 0.3, "start")
        self.film.add(K.Type(f"{self.page:02d}", x, y, w, self.ts("page"), t + 0.2, role="label", rgb=self.col("muted"), motion="fade"))

    def fill_frame(self, cx, cy, t, rgb):
        """A full-frame colour field (title slides). Slightly larger than the frame for the push-in."""
        w, h = self.vis_w * 1.12, self.vis_h * 1.12
        self.film.add(K.Surface(cx - w / 2, cy - h / 2, w, h, t - 0.25, rgb, 0, "fill"))

    def grad(self):
        g = self.skin.get("number_gradient")
        return (self.col(g[0]), self.col(g[1])) if g else None

    def title_grad(self):
        g = self.skin.get("title_gradient")
        return (self.col(g[0]), self.col(g[1])) if g else None

    # ---------------------------------------------------------------- scenes
    def _title_like(self, b, cx, cy, t0, text, size_key, kicker=None, sub=None):
        fill = self.skin.get("title_fill")
        tc = self.col("on_accent") if fill else self.col("text")
        mc = self.col("on_accent") if fill else self.col("muted")
        ac = self.col("on_accent") if fill else self.col("accent")
        if fill:
            self.fill_frame(cx, cy, t0, self.col("accent"))
        if self.skin.get("eyebrow_sub") and sub and not kicker:
            kicker, sub = sub, None
        rows = []
        if kicker:
            rows.append(self.T(kicker, self.ts("eyebrow"), "label", ac, t0, frac=0.7, track=0.02))
        rows.append(self.T(text, self.ts(size_key), "display", tc, t0 + 0.08, gap=self.ts("eyebrow") * 1.1 if kicker else 0,
                           frac=0.78 if self.align == "start" else 0.86, leading=1.04, track=-0.02, gradient=None if fill else self.title_grad()))
        if sub:
            rows.append(self.T(sub, self.ts("body"), "body", mc, t0 + 0.35, gap=self.ts(size_key) * 0.38, frac=0.6, leading=1.35))
        if self.layout == "deck" and not fill:
            x, w = self.box(cx, 0.8, "start")
            bw = self.px * 72
            # short accent bar above the title block, slide-style
            top, bottom, widest, *_ = self.stack(rows, cx, cy + self.px * 20)
            self.film.add(K.Surface(x + w - bw if self.rtl else x, top - self.px * 46, bw, self.px * 8, t0, self.col("accent"), self.px * 4, "fill"))
            return
        top, bottom, widest, x, w = self.stack(rows, cx, cy)
        if not fill:
            self.wrap(top, bottom, widest, x, w, cx, t0)

    def ed_title(self, b, i, cx, cy, rot, t0, t1):
        self._title_like(b, cx, cy, t0, b["text"], "title", b.get("kicker"), b.get("sub"))
        if b.get("chapter", True):
            self.chapters.append((t0, b.get("chapter_title", b["text"])))

    def ed_chapter(self, b, i, cx, cy, rot, t0, t1):
        n = b.get("number")
        kick = b.get("kicker") or (f"{self.chapter_word().title()} {int(n):02d}" if n is not None else None)
        self._title_like(b, cx, cy, t0, b["title"], "chapter", kick, b.get("sub"))
        self.chapters.append((t0, b["title"]))

    def ed_end(self, b, i, cx, cy, rot, t0, t1):
        self._title_like(b, cx, cy, t0, b.get("text", ""), "end", b.get("kicker"), b.get("sub"))

    def ed_big_number(self, b, i, cx, cy, rot, t0, t1):
        res = self.doc.res()
        if self.layout == "deck" and b.get("title"):
            cy = self.body_center(cx, cy, self.header(b["title"], cx, cy, t0))
        v = b["value"]
        role = self.skin.get("number_font", "display")
        size = self.ts("number")
        rows = []
        if b.get("kicker"):
            rows.append(self.T(b["kicker"], self.ts("eyebrow"), "label", self.col("accent"), t0, frac=0.7, track=0.02))
        gap0 = self.ts("eyebrow") * 1.2 if rows else 0
        if isinstance(v, str):
            tw = E.text_width(res, v, size, role, -0.02)
            if tw > self.cw:
                size *= self.cw / tw
            rows.append(self.T(v, size, role, self.col("number", "accent"), t0 + 0.05, gap=gap0, frac=1.0, leading=1.0,
                               track=-0.03, gradient=self.grad()))
        else:
            frac = repr(float(v)).split(".")[1]
            dec = 0 if frac == "0" else min(3, len(frac))
            final = f"{b.get('prefix', '')}{float(v):,.{dec}f}{b.get('suffix', '')}"
            tw = E.text_width(res, final, size, role, -0.03)
            if tw > self.cw:
                size *= self.cw / tw
            r = self.T(final, size, role, self.col("number", "accent"), t0 + 0.05, gap=gap0, frac=1.0, leading=1.0, track=-0.03,
                       gradient=self.grad())
            r.update(kind="count", value=v, prefix=b.get("prefix", ""), suffix=b.get("suffix", ""), decimals=dec)
            rows.append(r)
        share = b.get("share")
        if share is None and b.get("of"):
            share = float(v) / float(b["of"])
        if share is not None:
            mw = min(self.cw * 0.5, max(self.px * 360, E.text_width(res, str(v), size, role) * 1.1))
            rows.append({"kind": "meter", "share": share, "w": mw, "thick": self.px * 8, "rgb": self.col("accent"), "t": t0 + 0.3,
                         "gap": size * 0.28, "frac": 0.5})
        if b.get("caption"):
            rows.append(self.T(b["caption"], self.ts("body"), "body", self.col("muted"), t0 + 0.45,
                               gap=size * (0.3 if share is None else 0.22), frac=0.55, leading=1.35))
        top, bottom, widest, x, w = self.stack(rows, cx, cy)
        self.wrap(top, bottom, widest, x, w, cx, t0)
        if self.layout == "deck":
            self.page_number(cx, cy, t0)

    def ed_photo(self, b, i, cx, cy, rot, t0, t1):
        key = b["photo"]
        meta = self.doc.meta.get(key)
        if meta is None:
            raise SystemExit(f"beat {i + 1}: photo {key!r} is not prepared. Add it to photos.json and run docuframe assets.")
        aspect = meta["w"] / meta["h"]
        label, caption = b.get("label"), b.get("caption")
        if self.layout == "deck" and label:
            start = self.header(label, cx, cy, t0)
            label = None
            l, top, r, bot = self.frame(cx, cy)
            cy = (start + bot) / 2
            avail_h = bot - start
        else:
            avail_h = self.vis_h - 2 * self.my
        texts = [x for x in (label, caption) if x]
        gap = self.px * 72
        skin = b.get("skin", self.skin.get("photo", "rounded"))
        if texts and not self.tall:
            pw = self.cw * 0.6
            pw = min(pw, avail_h * 0.92 * aspect)
            ph = pw / aspect
            left = cx - self.cw / 2
            pcx = (left + pw / 2) if self.rtl else (left + self.cw - pw / 2)
            tx = (left + pw + gap) if self.rtl else left
            tw = self.cw - pw - gap
            rows = []
            if label:
                rows.append(self.T(label, self.ts("eyebrow"), "label", self.col("accent"), t0 + 0.3, frac=1, track=0.02, align="start"))
            if caption:
                rows.append(self.T(caption, self.ts("body") * 1.15, "body", self.col("text"), t0 + 0.45,
                                   gap=self.ts("eyebrow") * 1.1 if label else 0, frac=1, leading=1.3, align="start"))
            self.stack(rows, cx, cy, box=(tx, tw))
            pcy = cy
        elif texts:
            pw = self.cw
            ph = min(pw / aspect, avail_h * 0.5)
            pw = ph * aspect
            rows = []
            if label:
                rows.append(self.T(label, self.ts("eyebrow"), "label", self.col("accent"), t0 + 0.3, frac=1, track=0.02, align="start"))
            if caption:
                rows.append(self.T(caption, self.ts("body") * 1.1, "body", self.col("text"), t0 + 0.45,
                                   gap=self.ts("eyebrow") * 1.1 if label else 0, frac=1, leading=1.3, align="start"))
            th = sum(K.Type(r["text"], 0, 0, self.cw, r["size"], 0, role=r["role"], leading=r["leading"]).height(self.doc.res()) + r["gap"]
                     for r in rows)
            total = ph + gap + th
            pcx, pcy = cx, cy - total / 2 + ph / 2
            self.stack(rows, cx, cy - total / 2 + ph + gap + th / 2, box=(cx - self.cw / 2, self.cw))
        else:
            pw = min(self.cw * 0.86, avail_h * 0.86 * aspect)
            ph = pw / aspect
            pcx, pcy = cx, cy
        pr = K.Photo(key, pcx, pcy, pw, t0, skin=skin, motion="rise", rot=0.0, label=None, label_t=None,
                     bar_rgb=self.col("accent"), ink=self.col("text"), paper=self.c.get("glass", self.c.get("paper", (255, 255, 255))),
                     seed=i + 1)
        self.film.add(pr)
        self.prints.append((i, pr))
        self.photos_used.append(key)
        m = b.get("mark")
        if m:
            x, y = pcx + (m.get("fx", 0.5) - 0.5) * pw, pcy + (m.get("fy", 0.5) - 0.5) * ph
            tm = self.t_of({"line": b.get("line"), "at": m.get("at")}) if m.get("at") else t0 + 1.0
            self.film.add(E.PenMark(m.get("kind", "ellipse"), x, y, m.get("w", 0.35) * pw, m.get("h", 0.3) * ph, t_in=tm,
                                    rot=0.0, rgb=self.col("mark", "accent"), width=self.px * 5))
        if self.layout == "deck":
            self.page_number(cx, cy, t0)

    def ed_quote(self, b, i, cx, cy, rot, t0, t1):
        if self.layout == "deck" and b.get("title"):
            cy = self.body_center(cx, cy, self.header(b["title"], cx, cy, t0))
        q = b["text"]
        quoted = f"«{q}»" if is_rtl(q) else f"“{q}”"
        rows = [self.T(quoted, self.ts("quote"), self.skin.get("quote_font", "body"), self.col("text"), t0 + 0.1, frac=0.74, leading=1.28,
                       track=-0.01)]
        who = " — ".join(x for x in (b.get("who"), b.get("when")) if x)
        if who:
            rows.append(self.T("— " + who if not is_rtl(who) else who, self.ts("caption"), "label", self.col("muted"), t0 + 0.6,
                               gap=self.ts("quote") * 0.9, frac=0.74))
        top, bottom, widest, x, w = self.stack(rows, cx, cy)
        self.wrap(top, bottom, widest, x, w, cx, t0, pad=self.px * 72)
        if self.layout == "deck":
            self.page_number(cx, cy, t0)

    def ed_list(self, b, i, cx, cy, rot, t0, t1):
        res = self.doc.res()
        items = b["items"]
        size = self.ts("list")
        bw = self.cw * (0.62 if self.align == "center" else 0.72)
        x0 = cx - bw / 2 if self.align == "center" else ((cx + self.cw / 2 - bw) if self.rtl else cx - self.cw / 2)
        num_w = size * 2.2
        row_gap = size * 0.9
        start = None
        if self.layout == "deck" and b.get("title"):
            start = self.header(b["title"], cx, cy, t0)
        texts = []
        for k, it in enumerate(items):
            txt = it["text"] if isinstance(it, dict) else it
            tk = self.t_of({"line": b.get("line"), "at": it.get("at")}) if isinstance(it, dict) and it.get("at") else t0 + 0.4 + k * 0.45
            body = K.Type(txt, 0, 0, bw - num_w, size, tk, role="body", rgb=self.col("text"), leading=1.3)
            texts.append((k, body, tk, body.height(res)))
        title_rows = []
        if b.get("title") and self.layout != "deck":
            title_rows.append(K.Type(b["title"], x0, 0, bw, self.ts("slide"), t0, role="display", rgb=self.col("text"), leading=1.1, track=-0.01))
        th = sum(t.height(res) for t in title_rows) + (size * 1.6 if title_rows else 0)
        total = th + sum(h for *_, h in texts) + row_gap * 2 * (len(texts) - 1)
        ccy = self.body_center(cx, cy, start) if start else cy
        y = ccy - total / 2
        for t in title_rows:
            t.y = y
            self.film.add(t)
            y += t.height(res) + size * 1.6
        if self.skin.get("wrap"):
            pad = self.px * 64
            self.surface(x0 - pad, y - th - pad, bw + 2 * pad, total + 2 * pad, t0 - 0.05)
        for n, (k, body, tk, h) in enumerate(texts):
            if n:
                self.film.add(K.Hairline(x0, y - row_gap, bw, tk - 0.1, self.col("muted"), 0.22, max(2.0, self.px * 1.2), self.rtl))
            num = K.Type(f"{k + 1:02d}", (x0 + bw - num_w) if self.rtl else x0, y, num_w, size, tk, role="label", rgb=self.col("accent"))
            body.x = x0 if self.rtl else x0 + num_w
            body.y = y
            self.film.add(num)
            self.film.add(body)
            y += h + row_gap * 2
        if self.layout == "deck":
            self.page_number(cx, cy, t0)

    def ed_comparison(self, b, i, cx, cy, rot, t0, t1):
        res = self.doc.res()
        if self.layout == "deck" and b.get("title"):
            cy = self.body_center(cx, cy, self.header(b["title"], cx, cy, t0))
        gap = self.px * 40
        pad = self.px * 56
        sides = [b["left"], b["right"]]
        if self.rtl:
            sides = sides[::-1]
        if self.tall:
            cwid = self.cw
        else:
            cwid = (min(self.cw, self.px * 1500) - gap) / 2
        built = []
        for k, side in enumerate(sides):
            tk = t0 + 0.1 + k * 0.4
            short = len(side["title"]) <= 6          # a value ("21", "~150") reads as a number
            rows = [self.T(side["title"], self.ts("number") * 0.62 if short else self.ts("slide") * 0.9,
                           self.skin.get("number_font", "display") if short else "display",
                           self.col("accent" if k else "text"), tk + 0.1, frac=1, leading=1.05, track=-0.02)]
            body = "\n".join(side.get("lines", []))
            if body:
                rows.append(self.T(body, self.ts("body"), "body", self.col("muted"), tk + 0.3, gap=self.ts("body") * 0.8, frac=1, leading=1.4))
            h = sum(K.Type(r["text"], 0, 0, cwid - 2 * pad, r["size"], 0, role=r["role"], leading=r["leading"]).height(res) + r["gap"] for r in rows)
            built.append((rows, h, tk))
        ch = max(h for _, h, _ in built) + 2 * pad
        panel = self.skin.get("panel", "surface")
        for k, (rows, h, tk) in enumerate(built):
            if self.tall:
                x, y = cx - cwid / 2, cy - ch - gap / 2 if k == 0 else cy + gap / 2
            else:
                x, y = cx - cwid - gap / 2 + k * (cwid + gap), cy - ch / 2
            if panel != "none":
                self.surface(x, y, cwid, ch, tk)
            self.stack([dict(r, align="center" if self.align == "center" else "start") for r in rows], cx, y + ch / 2,
                       box=(x + pad, cwid - 2 * pad))
        if self.layout == "deck":
            self.page_number(cx, cy, t0)

    def ed_timeline(self, b, i, cx, cy, rot, t0, t1):
        if self.layout == "deck" and b.get("title"):
            cy = self.body_center(cx, cy, self.header(b["title"], cx, cy, t0))
        evs = b["events"]
        times = []
        for k, ev in enumerate(evs):
            if ev.get("at") and b.get("line"):
                times.append(self.t_of({"line": ev.get("line", b["line"]), "at": ev["at"]}))
            else:
                times.append(t0 + 0.6 + (t1 - t0 - 1.2) * k / max(1, len(evs)))
        w = self.cw
        if b.get("title") and self.layout != "deck":
            hx, hw = self.box(cx, 0.8)
            self.film.add(K.Type(b["title"], hx, cy - self.ts("year") * 4.2, hw, self.ts("slide"), t0, role="display", rgb=self.col("text"),
                                 align="center" if self.align == "center" else "start", leading=1.1, track=-0.01))
        self.film.add(K.DotLine(cx - w / 2, cy, w, evs, times, t0, self.col("text"), self.col("accent"), self.col("muted"),
                                self.ts("year"), self.ts("label"), rtl=self.rtl))
        if self.layout == "deck":
            self.page_number(cx, cy, t0)

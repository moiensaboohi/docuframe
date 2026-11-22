"""The docuframe logo: a custom wordmark, every letter drawn from one frame construction.

  python tools/brand.py        # writes docs/media/logo/*.svg and *.png

Wordmark: every letter is built from the same parts — one stroke weight, rounded frame corners,
square joins where a stem meets a bowl — so "d", "o", "a" and "e" are all small frames.
Units: x-height = 100, ascender = 142. Everything scales from there.
"""
import pathlib

import skia

ROOT = pathlib.Path(__file__).resolve().parent.parent
INK, PAPER, ACCENT = (17, 17, 19), (247, 247, 245), (43, 108, 255)
T, XH, ASC, RC, GAP = 19.0, 100.0, 142.0, 27.0, 14.0     # stroke, x-height, ascender, centre-line corner radius, letter gap
H = T / 2


# ---------------------------------------------------------------- construction helpers
def _stroke(path):
    pt = skia.Paint(Style=skia.Paint.kStroke_Style, StrokeWidth=T, StrokeCap=skia.Paint.kButt_Cap,
                    StrokeJoin=skia.Paint.kMiter_Join, AntiAlias=True)
    out = skia.Path()
    pt.getFillPath(path, out)
    return out


def _union(*paths):
    acc = skia.Path()
    for p in paths:
        acc = skia.Op(acc, p, skia.PathOp.kUnion_PathOp)
    return acc


def _cut(p, rect):
    q = skia.Path()
    q.addRect(rect)
    return skia.Op(p, q, skia.PathOp.kDifference_PathOp)


def _bowl(w, radii):
    """Centre line of a frame-shaped bowl of outer width w, sitting on the baseline; radii (tl, tr, br, bl)."""
    rr = skia.RRect()
    rr.setRectRadii(skia.Rect.MakeLTRB(H, -XH + H, w - H, -H), [skia.Point(v, v) for v in radii])
    p = skia.Path()
    p.addRRect(rr)
    return p


def _line(*pts):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    return p


def _arch(p, x, top):
    """Append a quarter arc from a vertical going up at x into a horizontal going right at `top` (centre line)."""
    p.arcTo(skia.Rect.MakeLTRB(x, top, x + 2 * RC, top + 2 * RC), 180, 90, False)


# ---------------------------------------------------------------- letters
def g_d():
    w = 98
    return _union(_stroke(_bowl(w, (RC, 0, RC, RC))), _stroke(_line((w - H, -ASC), (w - H, -XH + H)))), w


def g_o():
    w = 96
    return _stroke(_bowl(w, (RC,) * 4)), w


def g_c():
    w = 90
    return _cut(_stroke(_bowl(w, (RC,) * 4)), skia.Rect.MakeLTRB(w - T - 4, -XH + T + 9, w + 2, -T - 9)), w


def g_u():
    w = 95
    p = skia.Path()
    p.moveTo(H, -XH)
    p.lineTo(H, -H - RC)
    p.arcTo(skia.Rect.MakeLTRB(H, -H - 2 * RC, H + 2 * RC, -H), 180, -90, False)
    p.lineTo(w - H, -H)
    return _union(_stroke(p), _stroke(_line((w - H, -XH), (w - H, 0)))), w


def g_f():
    w, xs = 58, 17 + H
    p = skia.Path()
    p.moveTo(xs, 0)
    p.lineTo(xs, -ASC + H + RC)
    _arch(p, xs, -ASC + H)
    p.lineTo(w, -ASC + H)
    return _union(_stroke(p), _stroke(_line((0, -XH + H), (w - 6, -XH + H)))), w


def g_r():
    w = 56
    p = skia.Path()
    p.moveTo(H, 0)
    p.lineTo(H, -XH + H + RC)
    _arch(p, H, -XH + H)
    p.lineTo(w, -XH + H)
    return _stroke(p), w


def g_a():
    w = 95
    return _union(_stroke(_bowl(w, (RC, 0, 0, RC))), _stroke(_line((w - H, -XH), (w - H, 0)))), w


def g_m():
    w = 150
    mid = w / 2
    top = -XH + H
    p = skia.Path()
    p.moveTo(H, 0)
    p.lineTo(H, top + RC)
    _arch(p, H, top)
    p.lineTo(mid - RC, top)
    p.arcTo(skia.Rect.MakeLTRB(mid - 2 * RC, top, mid, top + 2 * RC), 270, 90, False)
    p.lineTo(mid, 0)
    q = skia.Path()
    q.moveTo(mid, top + RC)
    _arch(q, mid, top)
    q.lineTo(w - H - RC, top)
    q.arcTo(skia.Rect.MakeLTRB(w - H - 2 * RC, top, w - H, top + 2 * RC), 270, 90, False)
    q.lineTo(w - H, 0)
    return _union(_stroke(p), _stroke(q)), w


def g_e():
    w = 95
    p = _union(_stroke(_bowl(w, (RC,) * 4)), _stroke(_line((H, -XH / 2 - 1), (w - H, -XH / 2 - 1))))
    return _cut(p, skia.Rect.MakeLTRB(w - T - 4, -XH / 2 + H + 4, w + 2, -T - 9)), w


GLYPHS = {"d": g_d, "o": g_o, "c": g_c, "u": g_u, "f": g_f, "r": g_r, "a": g_a, "m": g_m, "e": g_e}
KERN = {"fr": -10, "ra": -14, "rf": -6, "cu": -2, "uf": -4}


def wordmark(text="docuframe"):
    """The name as one path, baseline at y = 0, starting at x = 0. Returns (path, width)."""
    out, x = skia.Path(), 0.0
    for i, ch in enumerate(text):
        p, w = GLYPHS[ch]()
        p.offset(x, 0)
        out = _union(out, p)
        x += w + GAP + KERN.get(ch + (text[i + 1] if i + 1 < len(text) else ""), 0)
    return out, x - GAP


# ---------------------------------------------------------------- drawing
def _scaled(path, k, x, base):
    q = skia.Path(path)
    q.transform(skia.Matrix.Scale(k, k))
    q.offset(x, base)
    return q


def metrics(asc_px):
    """(ascender, stem, x-height) in px for a lockup whose ascender is asc_px tall."""
    k = asc_px / ASC
    return asc_px, T * k, XH * k


def draw_wordmark(c, x, base, asc_px, ink=INK):
    """The name on a baseline, its ascenders asc_px tall. Returns the width."""
    k = asc_px / ASC
    wp, ww = wordmark()
    c.drawPath(_scaled(wp, k, x, base), skia.Paint(Color=skia.Color(*ink), AntiAlias=True))
    return ww * k


# ---------------------------------------------------------------- SVG
def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def _svg_d(path, dx=0.0):
    it = skia.Path.Iter(path, True)
    out = []
    V = skia.Path.Verb
    while True:
        verb, pts = it.next()
        if verb == V.kDone_Verb:
            break
        if verb == V.kMove_Verb:
            out.append(f"M{pts[0].x() + dx:.2f} {pts[0].y():.2f}")
        elif verb == V.kLine_Verb:
            out.append(f"L{pts[1].x() + dx:.2f} {pts[1].y():.2f}")
        elif verb == V.kQuad_Verb:
            out.append(f"Q{pts[1].x() + dx:.2f} {pts[1].y():.2f} {pts[2].x() + dx:.2f} {pts[2].y():.2f}")
        elif verb == V.kConic_Verb:
            q = skia.Path.ConvertConicToQuads(pts[0], pts[1], pts[2], it.conicWeight(), 2)
            for j in range(1, len(q) - 1, 2):
                out.append(f"Q{q[j].x() + dx:.2f} {q[j].y():.2f} {q[j + 1].x() + dx:.2f} {q[j + 1].y():.2f}")
        elif verb == V.kCubic_Verb:
            out.append("C" + " ".join(f"{pt.x() + dx:.2f} {pt.y():.2f}" for pt in pts[1:]))
        elif verb == V.kClose_Verb:
            out.append("Z")
    return " ".join(out)


def svg(ink=INK):
    wp, ww = wordmark()
    pad = 14.0
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad:.2f} {-ASC - pad:.2f} {ww + 2 * pad:.2f} {ASC + 2 * pad:.2f}" '
            f'role="img" aria-label="docuframe"><path fill-rule="evenodd" d="{_svg_d(wp)}" fill="{_hex(ink)}"/></svg>\n')


def main():
    out = ROOT / "docs" / "media" / "logo"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*"):
        old.unlink()
    files = {"docuframe-logo.svg": svg(), "docuframe-logo-dark.svg": svg(ink=(245, 245, 243))}
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
    for name, bg, ink in (("docuframe-logo.png", PAPER, INK), ("docuframe-logo-dark.png", (14, 14, 16), (245, 245, 243))):
        s = skia.Surface(1600, 400)
        c = s.getCanvas()
        c.clear(skia.Color(*bg))
        w = wordmark()[1] * 150 / ASC
        draw_wordmark(c, (1600 - w) / 2, 200 + 150 / 2, 150, ink=ink)
        s.makeImageSnapshot().save(str(out / name), skia.kPNG)
    print("wrote", ", ".join(sorted(files) + ["docuframe-logo.png", "docuframe-logo-dark.png"]))


if __name__ == "__main__":
    main()

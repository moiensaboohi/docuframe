"""The docuframe logo: one source for the mark, the wordmark and the files made from them.

  python tools/brand.py        # writes docs/media/logo/*.svg and *.png

The mark is a lowercase "d" built from a video frame: the frame is the bowl, its right side
rises into the stem. It is drawn from the wordmark's own metrics (x-height, ascender, stem
weight of Instrument Sans SemiBold), so mark and name read as one typeface.
"""
import pathlib

import skia
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT = pathlib.Path.home() / ".cache" / "docuframe" / "fonts" / "InstrumentSans-w600.ttf"
INK, PAPER, ACCENT = (17, 17, 19), (247, 247, 245), (43, 108, 255)
NAME, TRACK, GAP = "docuframe", -0.025, 0.22         # tracking and mark-to-name gap, in em


def _typeface():
    if not FONT.exists():
        from docuframe import fonts as _f  # noqa: F401  (fetches and instances fonts on first use)
        from docuframe.text import FontBook
        FontBook({"display": ["Instrument Sans:600"]})
    return skia.Typeface.MakeFromFile(str(FONT))


def metrics(size):
    """(ascender of 'd', stem width of 'l', x-height) at this size, measured from the glyphs."""
    f = skia.Font(_typeface(), size)

    def bounds(ch):
        return f.getPath(f.textToGlyphs(ch)[0]).computeTightBounds()
    return -bounds("d").top(), bounds("l").width(), -bounds("x").top()


K = 0.5523  # cubic handle length for a quarter circle


def mark_contours(size):
    """The mark as two closed contours (outer outline, inner opening), y down, baseline at y = 0.
    Each contour is a list of ("M"|"L", x, y) and ("C", x1, y1, x2, y2, x, y) commands.
    One continuous outline: the stem runs straight down into the frame's right side (that corner is
    square), so there is no seam where the stem meets the frame."""
    asc, t, xh = metrics(size)
    h, w = asc, asc * 1.08
    top = -(xh + t * 0.15)                    # top edge of the frame
    ro = t * 1.1 + t / 2                       # outer corner radius
    ri = max(t * 0.35, ro - t)                 # inner corner radius

    def arc(x0, y0, x1, y1, cx, cy):
        # quarter circle from (x0,y0) to (x1,y1) around corner point (cx,cy)
        return ("C", x0 + (cx - x0) * K, y0 + (cy - y0) * K, x1 + (cx - x1) * K, y1 + (cy - y1) * K, x1, y1)

    outer = [("M", w - t, -h), ("L", w, -h), ("L", w, -ro), arc(w, -ro, w - ro, 0, w, 0), ("L", ro, 0),
             arc(ro, 0, 0, -ro, 0, 0), ("L", 0, top + ro), arc(0, top + ro, ro, top, 0, top), ("L", w - t, top)]
    l, tt, r, b = t, top + t, w - t, -t
    inner = [("M", l + ri, tt), ("L", r - ri, tt), arc(r - ri, tt, r, tt + ri, r, tt), ("L", r, b - ri),
             arc(r, b - ri, r - ri, b, r, b), ("L", l + ri, b), arc(l + ri, b, l, b - ri, l, b), ("L", l, tt + ri),
             arc(l, tt + ri, l + ri, tt, l, tt)]
    return {"w": w, "h": h, "contours": [outer, inner]}


def mark_geometry(size):
    g = mark_contours(size)
    return {"w": g["w"], "h": g["h"]}


def _skia_path(contours, dx=0.0, dy=0.0):
    p = skia.Path()
    p.setFillType(skia.PathFillType.kEvenOdd)
    for cont in contours:
        for cmd in cont:
            if cmd[0] == "M":
                p.moveTo(cmd[1] + dx, cmd[2] + dy)
            elif cmd[0] == "L":
                p.lineTo(cmd[1] + dx, cmd[2] + dy)
            else:
                p.cubicTo(cmd[1] + dx, cmd[2] + dy, cmd[3] + dx, cmd[4] + dy, cmd[5] + dx, cmd[6] + dy)
        p.close()
    return p


def _svg_d(contours):
    out = []
    for cont in contours:
        for cmd in cont:
            out.append(cmd[0] + " ".join(f"{v:.2f}" for v in cmd[1:]))
        out.append("Z")
    return " ".join(out)


def draw_mark(c, x, base, size, rgb=ACCENT):
    g = mark_contours(size)
    c.drawPath(_skia_path(g["contours"], x, base), skia.Paint(Color=skia.Color(*rgb), AntiAlias=True))
    return g["w"]


def draw_lockup(c, x, base, size, ink=INK, mark=ACCENT):
    """Mark + name on one baseline. Returns the total width."""
    w = draw_mark(c, x, base, size, mark)
    f = skia.Font(_typeface(), size)
    f.setSubpixel(True)
    glyphs = f.textToGlyphs(NAME)
    pen = x + w + size * GAP
    paint = skia.Paint(Color=skia.Color(*ink), AntiAlias=True)
    for gid, adv in zip(glyphs, f.getWidths(glyphs)):
        p = f.getPath(gid)
        if p:
            p.offset(pen, base)
            c.drawPath(p, paint)
        pen += adv + TRACK * size
    return pen - TRACK * size - x


# ---------------------------------------------------------------- SVG export
def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def _name_svg_path(size, x0):
    font = TTFont(str(FONT))
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font["head"].unitsPerEm
    out, pen_x = [], x0
    for ch in NAME:
        gname = cmap[ord(ch)]
        sp = SVGPathPen(gs)
        gs[gname].draw(TransformPen(sp, (scale, 0, 0, -scale, pen_x, 0)))
        out.append(sp.getCommands())
        pen_x += gs[gname].width * scale + TRACK * size
    return " ".join(out), pen_x - TRACK * size


def svg(kind="lockup", ink=INK, mark=ACCENT, size=100.0, pad=None):
    g = mark_contours(size)
    pad = size * 0.12 if pad is None else pad
    parts = [f'<path fill-rule="evenodd" d="{_svg_d(g["contours"])}" fill="{_hex(mark)}"/>']
    width = g["w"]
    if kind == "lockup":
        d, end = _name_svg_path(size, g["w"] + size * GAP)
        parts.append(f'<path d="{d}" fill="{_hex(ink)}"/>')
        width = end
    desc = size * 0.22
    vb = (-pad, -g["h"] - pad, width + 2 * pad, g["h"] + desc + 2 * pad)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb[0]:.2f} {vb[1]:.2f} {vb[2]:.2f} {vb[3]:.2f}" '
            f'role="img" aria-label="docuframe">' + "".join(parts) + "</svg>\n")


def main():
    out = ROOT / "docs" / "media" / "logo"
    out.mkdir(parents=True, exist_ok=True)
    files = {"docuframe-logo.svg": svg("lockup"),
             "docuframe-logo-dark.svg": svg("lockup", ink=(245, 245, 243)),
             "docuframe-mark.svg": svg("mark"),
             "docuframe-mark-mono.svg": svg("mark", mark=INK)}
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
    # PNGs: lockup on paper and on ink, and a square app icon (mark on a rounded tile)
    for name, bg, ink in (("docuframe-logo.png", PAPER, INK), ("docuframe-logo-dark.png", (14, 14, 16), (245, 245, 243))):
        s = skia.Surface(1600, 400)
        c = s.getCanvas()
        c.clear(skia.Color(*bg))
        w = draw_lockup(c, 0, 0, 180)
        c.clear(skia.Color(*bg))
        draw_lockup(c, (1600 - w) / 2, 200 + mark_geometry(180)["h"] / 2, 180, ink=ink)
        s.makeImageSnapshot().save(str(out / name), skia.kPNG)
    s = skia.Surface(512, 512)
    c = s.getCanvas()
    c.clear(skia.Color(0, 0, 0, 0))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeWH(512, 512), 112, 112), skia.Paint(Color=skia.Color(*ACCENT), AntiAlias=True))
    g = mark_geometry(330)
    draw_mark(c, (512 - g["w"]) / 2, 256 + g["h"] / 2, 330, (255, 255, 255))
    s.makeImageSnapshot().save(str(out / "docuframe-icon.png"), skia.kPNG)
    print("wrote", ", ".join(sorted(files) + ["docuframe-logo.png", "docuframe-logo-dark.png", "docuframe-icon.png"]))


if __name__ == "__main__":
    main()

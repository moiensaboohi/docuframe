"""Build the README banner (docs/media/banner.png) from real frames rendered by docuframe.

  python tools/make_banner.py STILLS_ROOT

STILLS_ROOT holds _gallery_<style>/out/stills/16x9_t*.png folders, as written by
tools/style_gallery.py. Text is set with the engine's own font book, so every script in the
language block is shaped properly (joined Persian and Arabic, Devanagari conjuncts, CJK).
"""
import pathlib
import sys

import skia

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
from docuframe import engine as E          # noqa: E402
from docuframe.text import FontBook        # noqa: E402

W, H = 2400, 1200
BG, INK, MUTED, RULE = (247, 247, 245), (17, 17, 19), (104, 104, 110), (222, 222, 218)

# (style, which beat's still) — the best frame of each style; showcase films have 10 beats, classic 7
FRAMES = [("studio-light", 1), ("studio-dark", 2), ("editorial-collage", 0),
          ("swiss-grid", 4), ("briefing-room", 1), ("bold-poster", 3),
          ("slides-color", 0), ("lab-notebook", 2), ("midnight-minimal", 0),
          ("riso-print", 0), ("newsroom", 0), ("flat-explainer", 4)]

LANGS = [("Documentary", "English"), ("مستند", "Persian"), ("وثائقي", "Arabic"), ("वृत्तचित्र", "Hindi"),
         ("ドキュメンタリー", "Japanese"), ("纪录片", "Chinese"), ("Documental", "Spanish"), ("Belgesel", "Turkish")]


def para(book, text, size, role, rgb, width, align="left", leading=None, track=0.0):
    return book.paragraph(text, size, role, rgb, track, width=width, align=align, leading=leading)


def main():
    stills = pathlib.Path(sys.argv[1])
    book = FontBook({"display": ["Geist:600"], "body": ["Geist:400"], "label": ["Geist:500"], "mono": ["IBM Plex Mono"]})
    surf = skia.Surface(W, H)
    c = surf.getCanvas()
    c.clear(skia.Color(*BG))

    # ---- frames: 3 x 4 grid on the right
    gx0, gx1, gap = 1090, W - 110, 18
    fw = (gx1 - gx0 - 2 * gap) / 3
    fh = fw * 9 / 16
    gy0 = (H - (4 * fh + 3 * gap)) / 2
    for k, (style, beat) in enumerate(FRAMES):
        shots = sorted((stills / f"_gallery_{style}" / "out" / "stills").glob("16x9_t*.png"))
        img = skia.Image.open(str(shots[beat]))
        x = gx0 + (k % 3) * (fw + gap)
        y = gy0 + (k // 3) * (fh + gap)
        r = skia.Rect.MakeXYWH(x, y, fw, fh)
        rr = skia.RRect.MakeRectXY(r, 12, 12)
        c.drawRRect(skia.RRect.MakeRectXY(r.makeOffset(0, 6), 12, 12), E.fill((0, 0, 0), 0.07, 14))
        c.save()
        c.clipRRect(rr, True)
        c.drawImageRect(img, r, skia.SamplingOptions(skia.CubicResampler.Mitchell()))
        c.restore()
        c.drawRRect(rr, E.line((0, 0, 0), 0.08, 1.5))
        # name chip, bottom-left inside the frame
        p = para(book, style, 17, "mono", INK, 400)
        cw = p.LongestLine + 22
        chip = skia.Rect.MakeXYWH(x + 12, y + fh - 12 - 32, cw, 32)
        c.drawRRect(skia.RRect.MakeRectXY(chip, 8, 8), E.fill((255, 255, 255), 0.92))
        p.paint(c, chip.left() + 11, chip.top() + (32 - p.Height) / 2)

    # ---- text column on the left, aligned to the grid's top and bottom edges
    L, colw = 120, 860
    top, bottom = gy0, gy0 + 4 * fh + 3 * gap
    p = para(book, "docuframe", 38, "display", INK, colw)
    p.paint(c, L, top - 6)
    # headline: two deliberate lines, sized so the longer one fits the column
    lines = ["Give it a topic or a script.", "Get a finished documentary."]
    size = 80
    while max(para(book, ln, size, "display", INK, 5000, track=-0.02).LongestLine for ln in lines) > colw and size > 40:
        size -= 1
    y = top + 150
    p = para(book, "\n".join(lines), size, "display", INK, colw + 40, leading=1.08, track=-0.02)
    p.paint(c, L, y)
    y += p.Height + 34
    p = para(book, "An open-source agent skill: research, script, narration, motion graphics, captions and a "
                   "YouTube package. Drawn by code, every fact sourced.", 27, "body", MUTED, 760, leading=1.5)
    p.paint(c, L, y)
    # install command pinned to the grid's bottom edge
    cmd = "npx skills add moiensaboohi/docuframe"
    pc = para(book, cmd, 22, "mono", INK, colw)
    by = bottom - 58
    box = skia.Rect.MakeXYWH(L, by, pc.LongestLine + 44, 58)
    c.drawRRect(skia.RRect.MakeRectXY(box, 12, 12), E.fill((255, 255, 255), 1.0))
    c.drawRRect(skia.RRect.MakeRectXY(box, 12, 12), E.line(RULE, 1.0, 1.5))
    pc.paint(c, L + 22, by + (58 - pc.Height) / 2)
    # language block: words flow by their measured width, each with its language under it
    words = [(para(book, w, 30, "display", INK, 1000), para(book, n, 17, "body", MUTED, 1000)) for w, n in LANGS]
    gap_x, row_h = 34, 92
    rows, row, wsum = [], [], 0.0
    for wp, npg in words:
        cw = max(wp.LongestLine, npg.LongestLine)
        if row and wsum + gap_x + cw > colw:
            rows.append(row); row, wsum = [], 0.0
        row.append((wp, npg, cw)); wsum += (gap_x if len(row) > 1 else 0) + cw
    rows.append(row)
    block_h = len(rows) * row_h
    ly = by - 46 - block_h
    lab = para(book, "Narration, captions and on-screen text in any language", 20, "label", MUTED, colw)
    lab.paint(c, L, ly - lab.Height - 22)
    c.drawRect(skia.Rect.MakeXYWH(L, ly - lab.Height - 22 - 30, colw, 1.5), E.fill(RULE))
    for r_i, rw in enumerate(rows):
        x = L
        for wp, npg, cw in rw:
            wp.paint(c, x, ly + r_i * row_h)
            npg.paint(c, x, ly + r_i * row_h + 50)
            x += cw + gap_x
    y = by + 58

    out = ROOT / "docs" / "media" / "banner.png"
    surf.makeImageSnapshot().save(str(out), skia.kPNG)
    print(out, f"(text column ends at y={y + 58:.0f} of {H})")


if __name__ == "__main__":
    main()

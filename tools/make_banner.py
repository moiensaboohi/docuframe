"""Build the README banner (docs/media/banner.png) from real frames rendered by docuframe.

  python tools/make_banner.py SHOWCASE_PROJECT

Each tile is one style showing a different kind of scene (photo, number, title, timeline, map,
quote, list, comparison, chapter, lower third), rendered from the showcase project at a time when
that scene is settled. The last tile says there are many more styles, or make your own. Text is set with the
engine's own font book, so every script in the language block is shaped properly.
"""
import json
import pathlib
import shutil
import subprocess
import sys

import skia

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
from docuframe import engine as E          # noqa: E402
from docuframe.text import FontBook        # noqa: E402

W, H = 2400, 1200
BG, INK, MUTED, RULE = (247, 247, 245), (17, 17, 19), (104, 104, 110), (222, 222, 218)
ACCENT = (43, 108, 255)

# (style, seconds into the showcase film, what the tile shows, beats to drop, optional zoom (fx, fy, k)):
# zoom shows part of the real frame larger, centred on (fx, fy), so small type stays legible at README size
ZOOM = {"swiss-grid": (0.475, 0.45, 1.25), "slides-color": (0.42, 0.40, 1.3),
        "midnight-minimal": (0.32, 0.5, 1.8)}
TILES = [("studio-light", 6.45, "photo + caption", ["lower-third"]),
         ("studio-dark", 9.0, "number", []),
         ("editorial-collage", 2.4, "title", []),
         ("swiss-grid", 12.97, "timeline", []),
         ("briefing-room", 4.3, "map", []),
         ("bold-poster", 25.0, "quote", []),
         ("slides-color", 17.75, "list", []),
         ("lab-notebook", 20.3, "comparison", []),
         ("midnight-minimal", 22.7, "chapter", []),
         ("flat-explainer", 15.4, "number", []),
         ("newsroom", 6.45, "lower third", [])]

LANGS = [("Documentary", "English"), ("مستند", "Persian"), ("وثائقي", "Arabic"), ("वृत्तचित्र", "Hindi"),
         ("ドキュメンタリー", "Japanese"), ("纪录片", "Chinese"), ("Documental", "Spanish"), ("Belgesel", "Turkish")]


def para(book, text, size, role, rgb, width, align="left", leading=None, track=0.0):
    return book.paragraph(text, size, role, rgb, track, width=width, align=align, leading=leading)


def render_tile(proj, style, t, drop, scratch):
    work = scratch / f"tile_{style}"
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(proj, work, ignore=shutil.ignore_patterns("out"))
    plan = json.loads((work / "film.json").read_text(encoding="utf-8"))
    plan["style"] = style
    plan["beats"] = [b for b in plan["beats"] if b["scene"] not in drop]
    (work / "film.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    subprocess.run([sys.executable, "-m", "docuframe.cli", "render", "--project", str(work), "--stills", f"{t:.2f}"],
                   check=True, capture_output=True)
    return next((work / "out" / "stills").glob("16x9_t*.png"))


def all_styles():
    return sorted(p.name for p in (ROOT / "skills/docuframe/styles").iterdir() if (p / "style.json").exists())


def main():
    proj = pathlib.Path(sys.argv[1]).resolve()
    scratch = proj.parent / "_banner"
    scratch.mkdir(exist_ok=True)
    book = FontBook({"display": ["Geist:600"], "body": ["Geist:400"], "label": ["Geist:500"], "mono": ["IBM Plex Mono"]})
    surf = skia.Surface(W, H)
    c = surf.getCanvas()
    c.clear(skia.Color(*BG))

    # ---- grid: 3 x 4 on the right, last cell says how many more styles there are
    gx0, gx1, gap = 1100, W - 100, 18
    fw = (gx1 - gx0 - 2 * gap) / 3
    fh = fw * 9 / 16
    gy0 = (H - (4 * fh + 3 * gap)) / 2
    for k, (style, t, what, drop) in enumerate(TILES):
        img = skia.Image.open(str(render_tile(proj, style, t, drop, scratch)))
        x = gx0 + (k % 3) * (fw + gap)
        y = gy0 + (k // 3) * (fh + gap)
        r = skia.Rect.MakeXYWH(x, y, fw, fh)
        rr = skia.RRect.MakeRectXY(r, 12, 12)
        c.drawRRect(skia.RRect.MakeRectXY(r.makeOffset(0, 6), 12, 12), E.fill((0, 0, 0), 0.07, 14))
        c.save()
        c.clipRRect(rr, True)
        fx, fy, zk = ZOOM.get(style, (0.5, 0.5, 1.0))
        sw, sh = img.width() / zk, img.height() / zk
        sx = min(max(0.0, fx * img.width() - sw / 2), img.width() - sw)
        sy = min(max(0.0, fy * img.height() - sh / 2), img.height() - sh)
        c.drawImageRect(img, skia.Rect.MakeXYWH(sx, sy, sw, sh), r, skia.SamplingOptions(skia.CubicResampler.Mitchell()))
        c.restore()
        c.drawRRect(rr, E.line((0, 0, 0), 0.08, 1.5))
        p = para(book, style, 16, "mono", INK, 400)
        cw = p.LongestLine + 20
        # top-left: lower thirds and sources live at the bottom; slide styles keep their header top-left
        chip = (skia.Rect.MakeXYWH(x + fw - 10 - cw, y + fh - 40, cw, 30) if style.startswith("slides")
                else skia.Rect.MakeXYWH(x + 10, y + 10, cw, 30))
        c.drawRRect(skia.RRect.MakeRectXY(chip, 7, 7), E.fill((255, 255, 255), 0.94))
        p.paint(c, chip.left() + 10, chip.top() + (30 - p.Height) / 2)
        print(f"tile {k + 1}: {style} — {what}")
    k = len(TILES)
    x = gx0 + (k % 3) * (fw + gap)
    y = gy0 + (k // 3) * (fh + gap)
    r = skia.Rect.MakeXYWH(x, y, fw, fh)
    c.drawRRect(skia.RRect.MakeRectXY(r, 12, 12), E.fill(INK))
    p = para(book, "+ lots more styles", 40, "display", (255, 255, 255), fw - 48, track=-0.02)
    q = para(book, "or make your own", 24, "label", (170, 170, 178), fw - 48)
    ty = y + (fh - p.Height - 10 - q.Height) / 2
    p.paint(c, x + 28, ty)
    q.paint(c, x + 29, ty + p.Height + 10)

    # ---- text column, aligned to the grid's top and bottom edges
    L, colw = 110, 900
    top, bottom = gy0, gy0 + 4 * fh + 3 * gap
    # name: the hero. Page-fold frame mark + the custom frame-built wordmark (tools/brand.py)
    import brand
    probe = skia.Surface(10, 10).getCanvas()
    asc = 100 * (colw - 80) / brand.draw_lockup(probe, 0, 0, 100)     # lockup width = column width - 80
    base = top + asc
    brand.draw_lockup(c, L, base, asc, ink=INK, mark_rgb=ACCENT)
    y = base + 96
    lines = ["Give it a topic or a script.", "Get a finished documentary."]
    size = 56
    while max(para(book, ln, size, "display", INK, 5000, track=-0.015).LongestLine for ln in lines) > colw - 40 and size > 36:
        size -= 1
    p = para(book, "\n".join(lines), size, "display", INK, colw, leading=1.14, track=-0.015)
    p.paint(c, L, y)
    y += p.Height + 24
    p = para(book, "An open-source agent skill: research, script, narration, motion graphics, captions and a "
                   "YouTube package. Drawn by code, every fact sourced.", 25, "body", MUTED, 760, leading=1.5)
    p.paint(c, L, y)
    # install command pinned to the grid's bottom edge
    pc = para(book, "npx skills add moiensaboohi/docuframe", 21, "mono", INK, colw)
    by = bottom - 56
    box = skia.Rect.MakeXYWH(L, by, pc.LongestLine + 42, 56)
    c.drawRRect(skia.RRect.MakeRectXY(box, 12, 12), E.fill((255, 255, 255)))
    c.drawRRect(skia.RRect.MakeRectXY(box, 12, 12), E.line(RULE, 1.0, 1.5))
    pc.paint(c, L + 21, by + (56 - pc.Height) / 2)
    # language block: each word in its own script, its language under it, then "+ any language"
    items = [(para(book, w, 29, "display", INK, 1000), para(book, n, 16, "body", MUTED, 1000)) for w, n in LANGS]
    items.append((para(book, "+ any language", 29, "display", ACCENT, 1000),
                  para(book, "narration, captions, text", 16, "body", MUTED, 1000)))
    gap_x, row_h = 32, 88
    rows, row, wsum = [], [], 0.0
    for wp, npg in items:
        cw = max(wp.LongestLine, npg.LongestLine)
        if row and wsum + gap_x + cw > colw:
            rows.append(row)
            row, wsum = [], 0.0
        row.append((wp, npg, cw))
        wsum += (gap_x if len(row) > 1 else 0) + cw
    rows.append(row)
    ly = by - 44 - len(rows) * row_h
    lab = para(book, "Speaks your audience's language", 19, "label", MUTED, colw)
    lab.paint(c, L, ly - lab.Height - 20)
    c.drawRect(skia.Rect.MakeXYWH(L, ly - lab.Height - 20 - 28, colw - 40, 1.5), E.fill(RULE))
    for ri, rw in enumerate(rows):
        x = L
        for wp, npg, cw in rw:
            wp.paint(c, x, ly + ri * row_h)
            npg.paint(c, x, ly + ri * row_h + 48)
            x += cw + gap_x

    out = ROOT / "docs" / "media" / "banner.png"
    surf.makeImageSnapshot().save(str(out), skia.kPNG)
    print(out)


if __name__ == "__main__":
    main()

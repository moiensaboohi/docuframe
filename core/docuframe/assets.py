"""Prepare images: grade every photo into one consistent look, and generate the board textures.

  docuframe assets --project P              # grade from photos.json "grade" (bw | sepia | natural)
  docuframe assets --project P --grade natural

photos.json: {"grade": "bw", "photos": [{"id": "P01", "file": "x.jpg", "kind": "photo", "crop": [l, t, r, b]}]}
kind: photo (graded), doc (records and forms: colour mostly removed, paper tone kept),
      paper (newsprint: inky), color (kept in colour, slightly warmed).
crop: optional fractions of the image to keep.

Textures are made from noise in code (nothing downloaded): cork, cork_dark, paper, slate, charcoal,
studio, night, blueprint, and flat-R-G-B.png for any colour a style asks for.
Writes assets/prep/photos/<id>.jpg + meta.json and assets/prep/<texture>.png.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ImageOps

LONGEST = 3200
# duotone ends (shadow, paper) for each monochrome grade
INKS = {"bw": ("#101011", "#eeece6"), "sepia": ("#1e150e", "#f1e2c6")}


def _rgb(im):
    if im.mode in ("RGBA", "LA", "P", "PA"):
        im = im.convert("RGBA")
        flat = Image.new("RGB", im.size, (236, 230, 216))
        flat.paste(im, mask=im.getchannel("A"))
        return flat
    return im.convert("RGB")


def _cropped(im, frac):
    if not frac:
        return im
    W, H = im.size
    l, t, r, b = frac
    return im.crop((round(l * W), round(t * H), round(r * W), round(b * H)))


def grade(im, kind, look):
    """One consistent look for every image in a film."""
    rgb = _rgb(im)
    if look == "natural" or kind == "color":
        out = ImageEnhance.Color(ImageOps.autocontrast(rgb, cutoff=0.5)).enhance(0.92 if look == "natural" else 1.0)
        warm = Image.new("RGB", out.size, (255, 236, 214))
        return Image.blend(out, ImageChops.multiply(out, warm), 0.35)
    if look.startswith("duotone"):          # "duotone:#20304a:#f2e8d5" — a style's own two inks
        _, dark, light = look.split(":")
        return ImageOps.colorize(ImageEnhance.Contrast(ImageOps.autocontrast(ImageOps.grayscale(rgb), cutoff=1.0)).enhance(1.12),
                                 black=dark, white=light)
    shadow, paper = INKS.get(look, INKS["bw"])
    if kind == "doc":           # records and forms: keep a hint of the paper's colour
        return ImageEnhance.Color(rgb).enhance(0.4)
    gray = ImageOps.grayscale(rgb)
    if kind == "paper":         # newsprint: ink a little lifted
        return ImageOps.colorize(ImageOps.autocontrast(gray, cutoff=0.5), black="#24201c", white=paper)
    punchy = ImageEnhance.Contrast(ImageOps.autocontrast(gray, cutoff=1.0)).enhance(1.1)
    return ImageOps.colorize(punchy, black=shadow, white=paper, mid="#7d7a74" if look == "bw" else "#8a7458")


def prep_photos(proj, look, style_grade=None):
    spec = json.loads((proj / "photos.json").read_text(encoding="utf-8"))
    look = look or (spec.get("grade") if spec.get("grade") not in (None, "auto") else None) or style_grade or "bw"
    folder = proj / "assets" / "prep" / "photos"
    folder.mkdir(parents=True, exist_ok=True)
    sizes, waiting = {}, []
    for entry in spec.get("photos", []):
        src = proj / "assets" / "photos" / entry["file"] if entry.get("file") else None
        if not (src and src.exists()):
            waiting.append(entry["id"])
            continue
        pic = _cropped(Image.open(src), entry.get("crop"))
        pic.thumbnail((LONGEST, LONGEST), Image.LANCZOS)
        done = grade(pic, entry.get("kind", "photo"), look)
        done.save(folder / f"{entry['id']}.jpg", quality=92)
        sizes[entry["id"]] = {"w": done.width, "h": done.height, "kind": entry.get("kind", "photo")}
    (folder / "meta.json").write_text(json.dumps(sizes, indent=1), encoding="utf-8")
    (folder / "grade.txt").write_text(look, encoding="utf-8")
    note = f"; waiting for files: {', '.join(waiting)} (docuframe archive fetch)" if waiting else ""
    print(f"photos: {len(sizes)} prepared ({look}){note}")
    return not waiting


# ---------------------------------------------------------------- textures
def _octaves(n, seed, sizes=(4, 8, 16, 32, 64), falloff=0.55):
    """Tileable value noise: random grids of growing detail, each wrapped and smoothly enlarged."""
    rnd = np.random.default_rng(seed)
    total, amp, norm = np.zeros((n, n), np.float32), 1.0, 0.0
    for cells in sizes:
        grid = rnd.random((cells, cells)).astype(np.float32)
        tiled = np.tile(grid, (3, 3))                       # wrap so the edges join up
        big = Image.fromarray(tiled, mode="F").resize((n * 3, n * 3), Image.BICUBIC)
        total += amp * np.asarray(big, np.float32)[n:2 * n, n:2 * n]
        norm += amp
        amp *= falloff
    total /= norm
    return (total - total.min()) / max(1e-6, total.max() - total.min())


def _tint(v, dark, light):
    v = v[..., None]
    return np.asarray(dark, np.float32) * (1 - v) + np.asarray(light, np.float32) * v


def _cork(n=1024):
    v = _octaves(n, 1)
    specks = np.random.default_rng(2).random((n, n)) < 0.025
    v = np.where(specks, v * 0.6, v)
    return _tint(v, (88, 58, 36), (180, 136, 90))


def _flat(rgb, seed, n=1024, amount=0.06):
    v = _octaves(n, seed, sizes=(2, 4, 8, 64, 128), falloff=0.5)
    return np.asarray(rgb, np.float32) * (1 + (v[..., None] - 0.5) * 2 * amount)


def _paper(n=1024):
    return _flat((226, 220, 206), 5, n, 0.05)


def _blueprint(n=1024):
    base = _flat((18, 44, 86), 8, n, 0.08)
    grid = np.zeros((n, n), np.float32)
    for every, strength in ((n // 32, 0.07), (n // 8, 0.18)):
        grid[::every, :] = strength
        grid[:, ::every] = np.maximum(grid[:, ::every], strength)
    return base + grid[..., None] * 255


MAKERS = {
    "cork.png": _cork,
    "cork_dark.png": lambda: _tint(_octaves(1024, 1), (22, 15, 10), (70, 50, 34)),
    "paper.png": _paper,
    "slate.png": lambda: _flat((36, 42, 48), 21),
    "charcoal.png": lambda: _flat((30, 29, 28), 31, amount=0.1),
    "studio.png": lambda: _flat((222, 220, 216), 41, amount=0.02),
    "night.png": lambda: _flat((16, 20, 32), 51, amount=0.09),
    "blueprint.png": _blueprint,
}


def textures(prep, force=False, extra=()):
    """Write the board textures a film needs (only the missing ones unless force)."""
    prep = pathlib.Path(prep)
    prep.mkdir(parents=True, exist_ok=True)
    names = set(extra)
    made = []
    for name in sorted(names):
        p = prep / name
        if p.exists() and not force:
            continue
        if name in MAKERS:
            arr = MAKERS[name]()
        elif name.startswith("flat-") and name.endswith(".png"):
            r, g, b = (int(v) for v in name[5:-4].split("-")[:3])
            arr = _flat((r, g, b), 61)
        else:
            raise SystemExit(f"unknown board texture {name!r}; use one of {', '.join(MAKERS)} or flat-R-G-B.png")
        Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(p)
        made.append(name)
    if made:
        print("textures:", ", ".join(made))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--grade", default=None, choices=["bw", "sepia", "natural"])
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    plan = proj / "film.json"
    st = None
    if plan.exists():
        from . import styles as S
        st = S.load(json.loads(plan.read_text(encoding="utf-8")).get("style", "evidence-board"), proj)
    if (proj / "photos.json").exists():
        prep_photos(proj, a.grade, st.get("photo_grade") if st else None)
    if st and st.get("ground", {}).get("kind", "texture") == "texture":
        textures(proj / "assets" / "prep", extra=[st["finish"]["board"]])

"""Make stand-in photos for tests and CI (no network): procedural, ours, CC0.

  python tools/placeholder_photos.py PROJECT    # writes assets/photos/<id>.jpg for every photos.json entry without a file
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def make(seed, w=1600, h=1100):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    sky = 170 + 50 * (1 - y / h)
    img = np.repeat(sky[..., None], 3, 2)
    im = Image.fromarray(img.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for i in range(14):  # buildings
        bx = rng.uniform(-100, w); bw = rng.uniform(120, 360); bh = rng.uniform(200, 700)
        g = int(rng.uniform(40, 120))
        d.rectangle([bx, h - bh, bx + bw, h], fill=(g, g, g))
        for wy in range(int(h - bh + 30), h - 40, 60):
            for wx in range(int(bx + 20), int(bx + bw - 20), 50):
                if rng.random() < 0.6:
                    d.rectangle([wx, wy, wx + 18, wy + 28], fill=(g + 60, g + 60, g + 55))
    d.polygon([(0, h * 0.8), (w * 0.4, h * 0.7), (w, h * 0.85), (w, h), (0, h)], fill=(30, 28, 26))
    a = np.asarray(im.filter(ImageFilter.GaussianBlur(1.2)), np.float32)
    a += rng.standard_normal(a.shape[:2])[..., None] * 14
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def main(proj):
    proj = pathlib.Path(proj)
    spec = json.loads((proj / "photos.json").read_text(encoding="utf-8"))
    out = proj / "assets" / "photos"; out.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(spec["photos"]):
        if not p.get("file"):
            p["file"] = f"{p['id']}.jpg"
            make(100 + i).save(out / p["file"], quality=90)
            p.update(license="CC0 (test placeholder)", credit="docuframe test placeholder", license_ok=True, placeholder=True)
    (proj / "photos.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
    print("placeholders written to", out)


if __name__ == "__main__":
    main(sys.argv[1])

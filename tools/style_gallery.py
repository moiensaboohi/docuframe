"""Render one showcase project in many styles and build a gallery sheet (one row per style).

  python tools/style_gallery.py PROJECT OUT.jpg style-a style-b ...   (no styles = every built-in pack)

Each style is rendered into a scratch copy of PROJECT (film.json "style" swapped), one still per
beat taken 1.6 s after the beat starts, so every scene in the film appears in the sheet.
"""
import json
import pathlib
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))


def beat_starts(proj):
    from docuframe import engine as E
    from docuframe import scenes
    doc = E.Doc(proj)
    plan = scenes.load_plan(proj)
    b = scenes.Builder.__new__(scenes.Builder)
    b.doc, b.marks = doc, []
    return [scenes.Builder.t_of(b, beat) for beat in plan["beats"]], doc.duration


def main():
    proj, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    names = sys.argv[3:] or sorted(p.name for p in (ROOT / "skills/docuframe/styles").iterdir() if (p / "style.json").exists())
    starts, dur = beat_starts(proj)
    # after the entrance settles, before the camera leaves for the next beat
    times = [max(t + 0.9, min(t + 1.6, (starts[k + 1] - 1.0) if k + 1 < len(starts) else dur - 0.2)) for k, t in enumerate(starts)]
    rows = []
    for name in names:
        work = proj.parent / f"_gallery_{name}"
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(proj, work, ignore=shutil.ignore_patterns("out"))
        plan = json.loads((work / "film.json").read_text(encoding="utf-8"))
        plan["style"] = name
        (work / "film.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        subprocess.run([sys.executable, "-m", "docuframe.cli", "render", "--project", str(work), "--stills",
                        ",".join(f"{t:.2f}" for t in times)], check=True, capture_output=True)
        shots = sorted((work / "out" / "stills").glob("*_t*.png"))
        rows.append((name, shots))
        print(name, len(shots))
    tw, th, per = 448, 252, 5
    n = max(len(s) for _, s in rows)
    lines = (n + per - 1) // per
    block = 40 + lines * (th + 10) + 16
    sheet = Image.new("RGB", (20 + per * (tw + 10), len(rows) * block + 20), (22, 22, 24))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for r, (name, shots) in enumerate(rows):
        y = 20 + r * block
        d.text((20, y), name, fill=(235, 235, 235), font=font)
        for k, s in enumerate(shots):
            sheet.paste(Image.open(s).convert("RGB").resize((tw, th)), (20 + (k % per) * (tw + 10), y + 36 + (k // per) * (th + 10)))
    sheet.save(out, quality=85)
    print(out)


if __name__ == "__main__":
    main()

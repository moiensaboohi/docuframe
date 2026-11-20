"""Share: a short preview clip, a poster frame and a ready-to-post caption.

  docuframe share --project P                    # first 15 s of the film
  docuframe share --project P --t0 30 --len 12 --no-credit

Writes out/share/preview.mp4, poster.jpg and post.txt. post.txt ends with an optional
"made with docuframe" line you can delete (or leave out with --no-credit). No watermark is ever
added to your video.
"""
from __future__ import annotations

import argparse
import json
import pathlib

from .util import run


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--video", default=None)
    ap.add_argument("--t0", type=float, default=0.0)
    ap.add_argument("--len", type=float, default=15.0)
    ap.add_argument("--no-credit", action="store_true")
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    plan = json.loads((proj / "film.json").read_text(encoding="utf-8"))
    video = pathlib.Path(a.video) if a.video else proj / "out" / f"{proj.name}_{plan.get('format', '16:9').replace(':', 'x')}.mp4"
    if not video.exists():
        cands = sorted((proj / "out").glob("*.mp4"))
        if not cands:
            raise SystemExit("No rendered film yet. Run docuframe render first.")
        video = cands[0]
    sd = proj / "out" / "share"; sd.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a.t0:.2f}", "-i", video, "-t", f"{a.len:.2f}", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-movflags", "+faststart", sd / "preview.mp4"], "Making the preview clip failed")
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a.t0 + min(3.0, a.len / 2):.2f}", "-i", video, "-frames:v", "1", sd / "poster.jpg"])
    script = json.loads((proj / "script.json").read_text(encoding="utf-8"))
    titles = plan.get("package", {}).get("titles") or [script.get("title", proj.name)]
    post = [titles[0], "", plan.get("package", {}).get("hook") or "", ""]
    if not a.no_credit:
        post.append("(made with docuframe — delete this line if you like)")
    (sd / "post.txt").write_text("\n".join(x for x in post if x is not None).strip() + "\n", encoding="utf-8")
    print(f"share: {sd / 'preview.mp4'}, poster.jpg, post.txt")

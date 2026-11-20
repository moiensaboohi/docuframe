"""Burn captions into a finished video, without re-rendering the film.

  docuframe burn --project P --video out/film.mp4 --style highlighter --out out/film_captions.mp4

Each caption state (a cue, or for "highlighter" each word of a cue) is drawn once as a transparent
image; an ffmpeg concat list says how long each image stays up (a blank image fills the gaps), and a
single ffmpeg pass lays that image track over the video. Fast, and the film is never decoded in Python.
"""
from __future__ import annotations

import argparse
import json
import pathlib

from PIL import Image

from .util import run


def probe(video):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
               "-of", "json", video], "Reading the video failed")
    d = json.loads(out)
    return d["streams"][0]["width"], d["streams"][0]["height"], float(d["format"]["duration"])


def states(cap):
    """[(start, end, sample time)] at which the caption picture changes."""
    out = []
    for cue in cap.cues:
        marks = [cue["t0"]] + ([w_t for _, w_t in cue["words"][1:]] if cap.style == "highlighter" else [])
        marks = sorted(set(m for m in marks if cue["t0"] <= m < cue["t1"]))
        for a, b in zip(marks, marks[1:] + [cue["t1"]]):
            if b - a > 0.02:
                out.append((a, b, min(b - 0.01, a + 0.2)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--audio", default=None)
    ap.add_argument("--style", default="clean", choices=["clean", "highlighter", "bar"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    rel = lambda p: pathlib.Path(p) if pathlib.Path(p).is_absolute() else proj / p  # noqa: E731
    video, out = rel(a.video), rel(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    timing = json.loads((proj / "audio" / "timing.json").read_text(encoding="utf-8"))
    w, h, length = probe(video)
    from .captions import Captions
    cap = Captions(a.style, w, h, timing, proj / "fonts")
    work = proj / "out" / "burn"
    work.mkdir(parents=True, exist_ok=True)
    blank = work / "blank.png"
    Image.new("RGBA", (w, h), (0, 0, 0, 0)).save(blank)
    lines, clock = ["ffconcat version 1.0"], 0.0
    for k, (start, end, sample) in enumerate(states(cap)):
        if start > clock + 0.001:
            lines += [f"file '{blank.name}'", f"duration {start - clock:.3f}"]
        pic = work / f"c{k:05d}.png"
        Image.fromarray(cap.layer(sample), "RGBA").save(pic)
        lines += [f"file '{pic.name}'", f"duration {end - start:.3f}"]
        clock = end
    lines += [f"file '{blank.name}'", f"duration {max(0.04, length - clock):.3f}", f"file '{blank.name}'"]
    (work / "captions.ffconcat").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sound = rel(a.audio) if a.audio else video
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-f", "concat", "-safe", "0", "-i", work / "captions.ffconcat", "-i", sound,
         "-filter_complex", "[1:v]format=rgba[c];[0:v][c]overlay=0:0:format=auto:shortest=0:eof_action=pass[v]",
         "-map", "[v]", "-map", "2:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-t", f"{length:.3f}", "-movflags", "+faststart", out],
        "Burning the captions failed", "Delete out/burn and try again.")
    print(f"wrote {out}")

"""Shorts: 9:16 (or 1:1) cut-downs from the same project — same beats, re-laid out for the frame.

  docuframe shorts --project P                    # the hook: beats from the start up to ~55 s
  docuframe shorts --project P --t0 42 --t1 95    # a chosen stretch
  docuframe shorts --project P --format 1:1

The scene builder lays the world out as a column for vertical frames, so nothing is cropped off the
sides; docuframe check --format 9:16 verifies that no text sits under the app's buttons.
"""
from __future__ import annotations

import argparse
import json
import pathlib

from .render import render_film, size_for


def hook_end(proj, max_s=55.0):
    timing = json.loads((proj / "audio" / "timing.json").read_text(encoding="utf-8"))
    end = 0.0
    for s in timing["segments"]:
        if s["end"] + 0.4 > max_s:
            break
        end = s["end"] + 0.4
    return end or min(max_s, timing["total_duration"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--format", default="9:16")
    ap.add_argument("--t0", type=float, default=0.0)
    ap.add_argument("--t1", type=float, default=None)
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    t1 = a.t1 if a.t1 is not None else hook_end(proj)
    audio = proj / "audio" / ("mix.m4a" if (proj / "audio" / "mix.m4a").exists() else "narration.m4a")
    out = f"out/{proj.name}_short_{a.format.replace(':', 'x')}_{int(a.t0)}-{int(t1)}.mp4"
    render_film(proj, a.format, size_for(a.format, a.draft), "draft" if a.draft else "normal", 10.0, 0, audio, out, a.t0, t1)

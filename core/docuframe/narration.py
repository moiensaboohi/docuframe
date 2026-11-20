"""Join the narration lines into one track and write the timing the film is built on.

  docuframe narration --project P              # natural pace
  docuframe narration --project P --target 90  # fit the whole film to 90 s (0.9x-1.15x only)

Every line is trimmed to its speech, then placed with its own pause after it ("gap_after" in
script.json, else the defaults), so pacing is decided here, not by the voice engine's padding.
The track is levelled to -16 LUFS (spoken-word loudness for online video).
Reads audio/segments.json + audio/lines/segNN.wav; writes audio/narration.m4a and audio/timing.json.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import tempfile

import numpy as np

from . import audio as A
from .util import run

SPEEDS = (0.90, 1.15)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--target", type=float, default=None, help="total length in seconds")
    ap.add_argument("--lead", type=float, default=0.9, help="silence before the first line")
    ap.add_argument("--tail", type=float, default=1.8, help="silence after the last line")
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    adir = proj / "audio"
    sp = adir / "segments.json"
    if not sp.exists():
        raise SystemExit("No voice yet. Run docuframe voice first.")
    segs = json.loads(sp.read_text(encoding="utf-8"))["segments"]
    clips = []
    for s in segs:
        p = adir / "lines" / f"seg{s['id']:02d}.wav"
        if not p.exists():
            raise SystemExit(f"Line {s['id']} has no audio ({p.name}). Run docuframe voice again.")
        x = A.read(p)
        i0, i1 = A.speech_bounds(x)
        clips.append(x[i0:i1])
    speech = sum(len(c) for c in clips) / A.RATE
    pauses = a.lead + a.tail + sum(s.get("gap_after", 0.4) for s in segs[:-1])
    speed = 1.0
    if a.target:
        speed = speech / max(0.1, a.target - pauses)
        if not SPEEDS[0] <= speed <= SPEEDS[1]:
            raise SystemExit(f"Fitting {speech + pauses:.0f} s into {a.target:.0f} s needs {speed:.2f}x speed; "
                             f"beyond {SPEEDS[0]}-{SPEEDS[1]}x it sounds wrong. Shorten or lengthen the script instead.")
        if abs(speed - 1) > 0.005:
            with tempfile.TemporaryDirectory() as td:
                out = []
                for k, c in enumerate(clips):
                    src, dst = pathlib.Path(td) / f"i{k}.wav", pathlib.Path(td) / f"o{k}.wav"
                    A.write(src, c)
                    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter:a", f"atempo={speed:.4f}", dst], "Changing the pace failed")
                    out.append(A.read(dst))
                clips = out
    parts, timeline, t = [np.zeros(int(a.lead * A.RATE), np.float32)], [], a.lead
    for k, (s, c) in enumerate(zip(segs, clips)):
        dur = len(c) / A.RATE
        timeline.append({"id": s["id"], "scene": s.get("scene"), "caption": s["caption"], "vo": s["vo"],
                         "start": round(t, 3), "end": round(t + dur, 3)})
        parts.append(c)
        t += dur
        gap = a.tail if k == len(segs) - 1 else s.get("gap_after", 0.4)
        parts.append(np.zeros(int(gap * A.RATE), np.float32))
        t += gap
    track = np.concatenate(parts)
    raw = adir / "narration_raw.wav"
    A.write(raw, track)
    run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", str(A.RATE),
         "-c:a", "aac", "-b:a", "192k", adir / "narration.m4a"], "Levelling the narration failed")
    raw.unlink()
    voice = json.loads((adir / "voice.json").read_text(encoding="utf-8")) if (adir / "voice.json").exists() else {}
    total = round(len(track) / A.RATE, 3)
    (adir / "timing.json").write_text(json.dumps({"total_duration": total, "lead_in": a.lead, "tail_out": a.tail, "speed": round(speed, 4),
                                                  "lang": voice.get("lang"), "segments": timeline}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"narration: {total:.1f} s ({speech:.1f} s of speech, {len(segs)} lines) -> audio/narration.m4a, audio/timing.json")

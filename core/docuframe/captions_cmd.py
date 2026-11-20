"""Captions: SRT and VTT files from the narration timing, and optional burned-in captions.

  docuframe captions --project P                       # out/captions.srt + out/captions.vtt
  docuframe captions --project P --burn                # also out/<name>_captions.mp4 (style from the style pack)

Caption text is the script's display text (what the narrator says, written normally), chunked to
sentence-sized cues. Upload the SRT to YouTube with the clean render; burned-in captions are for
shorts and social clips. Cue text always matches the narration word for word (docuframe check verifies).
"""
from __future__ import annotations

import argparse
import json
import pathlib

from .captions import chunks_for, join_tokens


def ts(x, sep=","):
    ms = int(round(max(0.0, x) * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{sep}{ms % 1000:03d}"


def cues(timing, style="clean"):
    total = timing["total_duration"]
    out = []
    for c in chunks_for(timing, style):
        out.append({"t0": c["t0"], "t1": min(c["t1"], total), "text": join_tokens(w for w, _ in c["words"])})
    return out


def write(proj: pathlib.Path):
    timing = json.loads((proj / "audio" / "timing.json").read_text(encoding="utf-8"))
    cs = cues(timing)
    out = proj / "out"; out.mkdir(parents=True, exist_ok=True)
    srt = []
    vtt = ["WEBVTT", ""]
    for i, c in enumerate(cs, 1):
        srt += [str(i), f"{ts(c['t0'])} --> {ts(c['t1'])}", c["text"], ""]
        vtt += [f"{ts(c['t0'], '.')} --> {ts(c['t1'], '.')}", c["text"], ""]
    (out / "captions.srt").write_text("\n".join(srt), encoding="utf-8")
    (out / "captions.vtt").write_text("\n".join(vtt), encoding="utf-8")
    print(f"captions: out/captions.srt, out/captions.vtt ({len(cs)} cues)")
    return cs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--burn", action="store_true")
    ap.add_argument("--video", default=None)
    ap.add_argument("--style", default=None)
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    write(proj)
    if a.burn:
        plan = json.loads((proj / "film.json").read_text(encoding="utf-8"))
        from . import styles as S
        st = S.load(plan.get("style", "evidence-board"), proj)
        video = a.video or f"out/{proj.name}_{plan.get('format', '16:9').replace(':', 'x')}.mp4"
        audio = "audio/mix.m4a" if (proj / "audio" / "mix.m4a").exists() else "audio/narration.m4a"
        from . import burn
        burn.main(["--project", str(proj), "--video", video, "--audio", audio, "--style", a.style or st.get("captions", "clean"),
                   "--out", str(pathlib.Path(video).with_name(pathlib.Path(video).stem + "_captions.mp4"))])

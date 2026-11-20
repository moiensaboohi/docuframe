"""Self-review: check a project before (and after) the heavy render, and say what to fix.

  docuframe check --project P                 # every check; writes out/check.json and out/check.md
  docuframe check --project P --format 9:16

Checks (each explains why it matters):
  facts      every narrated claim links to a fact with a source; unsourced claims are flagged
             (the skill never invents facts, and viewers and YouTube reviewers check sources)
  numbers    every big number on screen has a source line
  licences   every photo has a recorded licence that allows commercial use, and a credit
  timing     how word times were measured (aligned: within 80 ms target; estimated: letter share)
  pacing     a visual change at least every 8 s; a hook (title or first hit) inside 10 s
  legibility on-screen text is at least 28 px tall at 1080p (overlays 24 px)
  framing    text fits inside the frame; in 9:16 nothing sits in the bottom 20% or top 10% (app UI)
  blank      no beat renders as an empty frame
  captions   caption cues match the narration word for word
  chapters   YouTube chapter rules: first at 0:00, at least 3, each at least 10 s
Exit code 1 when any check fails.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from . import engine as E

MIN_PX, MIN_OVERLAY_PX = 28, 24


class Report:
    def __init__(self):
        self.items = []

    def add(self, check, level, msg, fix=""):
        self.items.append({"check": check, "level": level, "msg": msg, "fix": fix})

    @property
    def failed(self):
        return any(i["level"] == "fail" for i in self.items)


def check_facts(proj, rep):
    sp = proj / "script.json"
    fp = proj / "facts.json"
    if not sp.exists():
        return
    from .voice import lines_of, load_script
    script = load_script(proj)
    facts = {f["id"]: f for f in json.loads(fp.read_text(encoding="utf-8"))["facts"]} if fp.exists() else {}
    if not fp.exists():
        rep.add("facts", "warn", "no facts.json: claims cannot be traced to sources", "Write facts.json (the fact sheet) and link each line's claims with \"facts\".")
    for _, ln in lines_of(script):
        ids = ln.get("facts")
        has_digit = any(ch.isdigit() for ch in ln["text"])
        if ids is None and not ln.get("opinion"):
            rep.add("facts", "fail" if has_digit else "warn", f"line {ln['id']} has no linked facts: {ln['text'][:70]!r}",
                    "Add \"facts\": [ids] from facts.json, or \"opinion\": true if it states no fact.")
            continue
        for fid in ids or []:
            f = facts.get(fid)
            if not f:
                rep.add("facts", "fail", f"line {ln['id']} cites {fid}, which is not in facts.json", "Add the fact with its source.")
            elif not any(s.get("url") or s.get("title") for s in f.get("sources", [])):
                rep.add("facts", "fail", f"fact {fid} has no source", "Add at least one source (title and URL).")


def check_beats(proj, b, rep):
    for i, beat in enumerate(b.plan["beats"]):
        if beat["scene"] in ("big-number", "timeline", "map") and not beat.get("source"):
            rep.add("numbers", "fail", f"beat {i + 1} ({beat['scene']}) shows data with no source line",
                    "Add \"source\" to the beat (it is shown on screen and listed in the description).")


def check_licences(proj, b, rep):
    pp = proj / "photos.json"
    if not pp.exists():
        return
    spec = json.loads(pp.read_text(encoding="utf-8"))
    used = set(b.photos_used)
    for p in spec.get("photos", []):
        if p["id"] not in used:
            continue
        if p.get("placeholder"):
            rep.add("licences", "warn", f"{p['id']} is a test placeholder, not a real photo", "Fetch the real image: docuframe archive fetch.")
            continue
        if not p.get("license"):
            rep.add("licences", "fail", f"{p['id']} has no recorded licence", "docuframe archive fetch records it; for your own photos set \"license\": \"own\".")
        elif p.get("license_ok") is False:
            rep.add("licences", "fail", f"{p['id']} licence {p['license']!r} may not allow commercial use", "Replace the image or get permission.")
        if p.get("license") and p.get("license") != "own" and not p.get("credit"):
            rep.add("licences", "warn", f"{p['id']} has no credit line", "Add \"credit\".")


def check_timing(doc, b, st, rep):
    method = doc.timing.get("alignment", {}).get("method")
    if method:
        rep.add("timing", "pass", f"word times aligned ({method}); hits are placed on aligned word starts (target ±80 ms)")
    else:
        rep.add("timing", "warn", "word times are estimated from letter share (typically 150-250 ms off)",
                "For tighter hits: pip install faster-whisper, then docuframe align.")
    starts = sorted(b.t_of(x) for x in b.plan["beats"])
    gaps = [(b2 - a2, a2) for a2, b2 in zip(starts, starts[1:] + [doc.duration])]
    mx = st["pacing"]["visual_change_s"][1]
    for k, (g, t) in enumerate(gaps):
        if g < 1.5:
            rep.add("pacing", "warn", f"beat {k + 1} is on screen for only {g:.1f} s (from {t:.1f} s)",
                    "Anchor it to an earlier word, or merge it with the next beat.")
    for g, t in gaps:
        if g > mx + 0.5:
            rep.add("pacing", "warn", f"{g:.1f} s without a new beat from {t:.1f} s (style asks for a change every ≤{mx} s)",
                    "Split the beat, add a mark/highlight, or a lower third.")
    if starts and starts[0] > st["pacing"]["hook_s"]:
        rep.add("pacing", "warn", f"first beat starts at {starts[0]:.1f} s", "Open with the hook inside 10 s.")


def text_items(film):
    from .scenes import TextBlock
    for it in film.items:
        if isinstance(it, E.BigText):
            yield it, it.text, it.size, it.font, it.x, it.y
        elif isinstance(it, E.Counter):
            yield it, f"{it.prefix}{it.value}{it.suffix}", it.size, it.font, it.x, it.y
            if it.caption:
                yield it, it.caption, it.size * 0.24, "cond", it.x, it.y + it.size * 0.42
        elif isinstance(it, TextBlock):
            yield it, it.text.split("\n")[0][:60], it.size, it.role, it.x, it.y + it.size * 0.8


def check_frames(proj, film, r, b, fmt, rep, outdir):
    from PIL import Image
    from .scenes import TextBlock
    from .render import beat_times
    times = beat_times(proj, fmt)
    starts = [b.t_of(x) for x in b.plan["beats"]]
    W, H = r.W, r.H
    short = min(W, H)
    outdir.mkdir(parents=True, exist_ok=True)
    for bi, t in enumerate(times):
        img = r.frame_rgb(int(t * film.fps))
        Image.fromarray(img).save(outdir / f"check_{bi + 1:02d}.png")
        if float(img.std()) < 6:
            rep.add("blank", "fail", f"beat {bi + 1} renders as an almost empty frame at {t:.1f} s", "Check the camera and the beat's time.")
        cx, cy, z, rot = film.camera(t)
        k = z * r.s
        for it, text, size, font, x, y in text_items(film):
            if not it.visible(t) or t < it.t_in + 0.6 or it.t_in < starts[bi] - 0.5:
                continue     # only text introduced in this beat is meant to be read now
            sx, sy = (x - cx) * k + W / 2, (y - cy) * k + H / 2
            if not (-W * 0.2 < sx < W * 1.2 and -H * 0.2 < sy < H * 1.2):
                continue     # not in this shot
            px = size * k * 1080 / short
            if px < MIN_PX:
                rep.add("legibility", "fail", f"beat {bi + 1}: {text[:30]!r} is {px:.0f} px tall at 1080p (min {MIN_PX})",
                        "Make it bigger, or let the camera move closer for this beat.")
            tw = E.text_width(r.res, text, size, font) * k if hasattr(it, "text") or isinstance(it, E.Counter) else 0
            if hasattr(it, "w") and isinstance(it, TextBlock):
                tw = min(tw, it.w * k)            # wrapped blocks are never wider than their box
            if tw and (sx - tw / 2 < W * 0.03 or sx + tw / 2 > W * 0.97):
                rep.add("framing", "fail", f"beat {bi + 1}: {text[:30]!r} runs outside the frame", "Shorten the text or reduce its size.")
            if H > W and (sy > H * 0.80 or sy < H * 0.10):
                rep.add("framing", "fail", f"beat {bi + 1}: {text[:30]!r} sits under the app's buttons/caption zone in 9:16",
                        "Move it toward the middle of the frame.")


def check_captions(proj, rep):
    tp = proj / "audio" / "timing.json"
    timing = json.loads(tp.read_text(encoding="utf-8"))
    from .captions_cmd import cues
    from .captions import _tokens
    joined = [t for c in cues(timing) for t in _tokens(c["text"])]
    want = [t for s in timing["segments"] for t in _tokens(s["caption"])]
    if joined != want:
        rep.add("captions", "fail", "caption cues do not match the narration text word for word", "Rebuild with docuframe captions.")
    else:
        rep.add("captions", "pass", f"captions match the narration ({len(want)} words)")


def check_chapters(b, duration, rep):
    ch = sorted(b.chapters)
    if len(ch) < 3:
        rep.add("chapters", "info", f"{len(ch)} chapter marker(s): YouTube shows chapters only with 3 or more (fine for shorts)")
        return
    if ch[0][0] > 1.0:
        rep.add("chapters", "warn", "first chapter is not at 0:00; the package will start it at 0:00")
    for (a, _), (c, n) in zip(ch, ch[1:]):
        if c - a < 10:
            rep.add("chapters", "fail", f"chapter {n!r} starts {c - a:.1f} s after the previous one (YouTube needs 10 s)", "Merge chapters.")


def run_checks(proj, fmt=None, frames=True):
    from .render import make, size_for
    proj = pathlib.Path(proj).resolve()
    plan = json.loads((proj / "film.json").read_text(encoding="utf-8"))
    fmt = fmt or plan.get("format", "16:9")
    film, r, b, st = make(proj, fmt, size_for(fmt, draft=False))
    rep = Report()
    check_facts(proj, rep)
    check_beats(proj, b, rep)
    check_licences(proj, b, rep)
    check_timing(b.doc, b, st, rep)
    if frames:
        check_frames(proj, film, r, b, fmt, rep, proj / "out" / "check")
    check_captions(proj, rep)
    check_chapters(b, b.doc.duration, rep)
    for note in r.res.book.notes:
        rep.add("fonts", "warn", note, "Run docuframe doctor to fetch fonts.")
    out = proj / "out"; out.mkdir(exist_ok=True)
    (out / "check.json").write_text(json.dumps({"format": fmt, "items": rep.items}, indent=1, ensure_ascii=False), encoding="utf-8")
    lines = [f"# Check — {proj.name} ({fmt})", ""]
    for lv, mark in (("fail", "✗"), ("warn", "!"), ("info", "i"), ("pass", "✓")):
        for i in rep.items:
            if i["level"] == lv:
                lines.append(f"- {mark} **{i['check']}**: {i['msg']}" + (f" — {i['fix']}" if i["fix"] else ""))
    (out / "check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--format", default=None)
    ap.add_argument("--no-frames", action="store_true")
    a = ap.parse_args(argv)
    rep = run_checks(a.project, a.format, not a.no_frames)
    fails = [i for i in rep.items if i["level"] == "fail"]
    warns = [i for i in rep.items if i["level"] == "warn"]
    for i in fails + warns:
        print(f"{'✗' if i['level'] == 'fail' else '!'} {i['check']}: {i['msg']}" + (f"\n    → {i['fix']}" if i["fix"] else ""))
    print(f"\ncheck: {len(fails)} to fix, {len(warns)} warnings — details in out/check.md, frames in out/check/")
    if fails:
        raise SystemExit(1)

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
import re
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


# ---------------------------------------------------------------- slop: defaults nobody chose
SLOP_PHRASES = ["did you know", "let's dive in", "let’s dive in", "dive into", "here's the thing", "here’s the thing", "in a world where",
                "untold story", "you won't believe", "you won’t believe", "mind-blowing", "mind blowing", "game-changer",
                "game changer", "revolutionary", "revolutionize", "revolutionise", "unlock", "unleash", "delve", "tapestry",
                "testament to", "ever-evolving", "navigating the", "buckle up", "stay tuned", "without further ado",
                "the secret behind", "changed everything", "shocking truth"]
SLOP_PATTERNS = [r"\bnot (?:just|only) [^,.;]{1,40}, but\b", r"\bit'?s not about [^,.;]{1,40}, it'?s about\b"]
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2190-\u21FF\uFE0F]")


def _beat_texts(beat):
    """(field, text) for everything a beat puts on screen."""
    out = []
    for k in ("text", "sub", "kicker", "caption", "label", "title", "who", "name", "role"):
        if isinstance(beat.get(k), str):
            out.append((k, beat[k]))
    for it in beat.get("items", []) or []:
        out.append(("item", it["text"] if isinstance(it, dict) else str(it)))
    for side in ("left", "right"):
        if isinstance(beat.get(side), dict):
            out.append(("title", beat[side].get("title", "")))
            out += [("line", x) for x in beat[side].get("lines", [])]
    for ev in beat.get("events", []) or []:
        out += [("label", str(ev.get("label", ""))), ("when", str(ev.get("when", "")))]
    return [(k, t) for k, t in out if t]


def _hue(rgb):
    import colorsys
    r, g, b = (v / 255 for v in rgb[:3])
    h, l, s_ = colorsys.rgb_to_hls(r, g, b)
    return None if s_ < 0.25 or l < 0.12 or l > 0.92 else h


def check_slop(proj, plan, st, rep):
    """Generated-looking choices: stock phrases, emoji, shouting, gradient text, glow, too many colours."""
    modern = (st.get("skin") or {}).get("layout", "center") != "center"
    hits = 0
    for i, beat in enumerate(plan.get("beats", [])):
        for field, txt in _beat_texts(beat):
            low = txt.lower()
            bad = [ph for ph in SLOP_PHRASES if ph in low] + [m.group(0) for pat in SLOP_PATTERNS for m in re.finditer(pat, low)]
            if bad:
                rep.add("slop", "warn", f"beat {i + 1} {field}: stock phrase {bad[0]!r} in {txt[:50]!r}",
                        "Say the specific fact instead (references/design.md).")
                hits += 1
            if EMOJI.search(txt):
                rep.add("slop", "warn", f"beat {i + 1} {field}: emoji or decorative symbol in {txt[:50]!r}", "Remove it; let the words carry it.")
                hits += 1
            if "!" in txt and field in ("text", "title", "kicker", "label", "sub", "caption"):
                rep.add("slop", "warn", f"beat {i + 1} {field}: exclamation mark in {txt[:50]!r}", "Drop it; the fact is the surprise.")
                hits += 1
            words = [w for w in re.split(r"\s+", txt) if any(ch.isalpha() for ch in w)]
            if modern and len(words) > 3 and txt.upper() == txt and any(ch.isalpha() and ch.isupper() for ch in txt):
                rep.add("slop", "warn", f"beat {i + 1} {field}: {len(words)} words in ALL CAPS: {txt[:50]!r}", "Use sentence case.")
                hits += 1
    narr = proj / "audio" / "timing.json"
    if narr.exists():
        try:
            segs = json.loads(narr.read_text(encoding="utf-8")).get("segments", [])
        except ValueError:
            segs = []
        for sg in segs:
            low = str(sg.get("caption") or sg.get("vo") or "").lower()
            bad = [ph for ph in SLOP_PHRASES if ph in low]
            if bad:
                rep.add("slop", "warn", f"narration line {sg.get('id')}: stock phrase {bad[0]!r}", "Rewrite the line around the fact.")
                hits += 1
    skin = st.get("skin") or {}
    if skin.get("number_gradient") or skin.get("title_gradient"):
        rep.add("slop", "warn", "style turns on gradient text", "Use one solid colour for numbers and titles.")
        hits += 1
    g = st.get("ground") or {}
    if g.get("kind") == "gradient" and sum(abs(a - b) for a, b in zip(g.get("color", [0, 0, 0]), g.get("color2", g.get("color", [0, 0, 0])))) > 45:
        rep.add("slop", "warn", "style ground is a visible colour gradient", "Use a flat ground; let photographs and type give depth.")
        hits += 1
    if (st.get("finish") or {}).get("glow", 0) > 0.12:
        rep.add("slop", "warn", f"style glow is {st['finish']['glow']}", "Keep glow under 0.12 unless the subject is light itself.")
        hits += 1
    cols = (st.get("tokens") or {}).get("color", {})
    hues = []
    for k in ("accent", "highlight", "label", "number", "mark"):
        h = _hue(cols[k]) if k in cols else None
        if h is not None and all(min(abs(h - x), 1 - abs(h - x)) > 0.06 for x in hues):
            hues.append(h)
    if len(hues) > 2:
        rep.add("slop", "warn", f"style uses {len(hues)} accent hues", "Pick one accent (two at most) and give it one job.")
        hits += 1
    if not hits:
        rep.add("slop", "pass", "no stock phrases, emoji, shouting, gradient text or colour sprawl")


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
    check_slop(proj, plan, st, rep)
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

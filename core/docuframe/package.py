"""Delivery: the YouTube package and manifest.json.

  docuframe package --project P

Writes out/youtube/:
  titles.txt        3 title options (from film.json "package.titles"; the agent writes them, the
                    script's title is the fallback)
  description.txt   hook line, chapters with timestamps, sources from the fact sheet, image credits,
                    font and voice credits, the AI-voice disclosure note where it applies
  tags.txt          from film.json "package.tags"
  thumb_1..3.jpg    1280x720 thumbnail frames (title beat, the biggest number, the strongest photo)
  upload-checklist.md   what to tick in YouTube Studio (altered/synthetic content, captions file)
and out/manifest.json: inputs, settings, versions, sources, licences, attribution lines, outputs,
and the one-line re-render command.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import platform

from . import __version__


def mmss(t):
    t = int(t)
    return f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


def sha(p: pathlib.Path):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()[:16]


def build(proj: pathlib.Path):
    from .render import make, size_for
    from .scenes import FORMATS
    plan = json.loads((proj / "film.json").read_text(encoding="utf-8"))
    fmt = plan.get("format", "16:9")
    film, r, b, st = make(proj, fmt, "1280x720" if fmt == "16:9" else size_for(fmt, False))
    script = json.loads((proj / "script.json").read_text(encoding="utf-8"))
    facts = json.loads((proj / "facts.json").read_text(encoding="utf-8")) if (proj / "facts.json").exists() else {"facts": []}
    photos = json.loads((proj / "photos.json").read_text(encoding="utf-8")) if (proj / "photos.json").exists() else {"photos": []}
    voice = json.loads((proj / "audio" / "voice.json").read_text(encoding="utf-8")) if (proj / "audio" / "voice.json").exists() else {}
    pk = plan.get("package", {})
    yt = proj / "out" / "youtube"; yt.mkdir(parents=True, exist_ok=True)

    title = script.get("title", proj.name)
    titles = (pk.get("titles") or [])[:3] or [title]
    (yt / "titles.txt").write_text("\n".join(titles) + "\n", encoding="utf-8")

    # chapters: YouTube needs the first at 0:00, at least 3, each >= 10 s
    ch = sorted(b.chapters)
    chapters = []
    for t, name in ch:
        if chapters and t - chapters[-1][0] < 10:
            continue
        chapters.append((0.0 if not chapters else t, name))
    use_chapters = len(chapters) >= 3

    srcs, seen = [], set()
    for f in facts.get("facts", []):
        for s in f.get("sources", []):
            key = s.get("url") or s.get("title")
            if key and key not in seen:
                seen.add(key)
                srcs.append(f"- {s.get('publisher', '')}{': ' if s.get('publisher') else ''}{s.get('title', '')} {s.get('url', '')}".strip())
    # thumbnails first: rendering them also loads every face the film uses
    # (title beat, biggest number, first photo)
    from PIL import Image
    picks = []
    beats = plan["beats"]
    starts = [b.t_of(x) for x in beats]
    ends = starts[1:] + [b.doc.duration]
    for kind in ("title", "big-number", "photo"):
        for i, x in enumerate(beats):
            if x["scene"] == kind:
                picks.append(min(ends[i] - 0.3, starts[i] + 1.6)); break
    thumbs = []
    for k, t in enumerate(picks[:3], 1):
        img = Image.fromarray(r.frame_rgb(int(t * film.fps)))
        if img.size != (1280, 720) and fmt == "16:9":
            img = img.resize((1280, 720))
        p = yt / f"thumb_{k}.jpg"; img.save(p, quality=92); thumbs.append(p.name)

    used = set(b.photos_used)
    fonts_used = sorted(r.res.book.loaded)
    credits = []
    for p in photos.get("photos", []):
        if p["id"] in used and p.get("license") != "own":
            credits.append(f"- {p.get('what', p['id'])}: {p.get('credit', 'unknown')}, {p.get('license', 'licence not recorded')}"
                           + (f" ({p['source']})" if p.get("source") else ""))
    synthetic_voice = bool(voice.get("synthetic"))
    lines = [pk.get("hook") or (script["takes"][0]["lines"][0]["text"] if script.get("takes") else title), ""]
    if pk.get("summary"):
        lines += [pk["summary"], ""]
    if use_chapters:
        lines += ["Chapters"] + [f"{mmss(t)} {n}" for t, n in chapters] + [""]
    if srcs:
        lines += ["Sources"] + srcs + [""]
    if credits:
        lines += ["Image credits"] + credits + [""]
    extra = []
    if fonts_used:
        extra.append("Fonts: " + ", ".join(fonts_used) + " (open font licences, see manifest)")
    if synthetic_voice:
        extra.append("Narration: synthetic voice" + (f" ({voice.get('engine')})" if voice.get("engine") else ""))
    if extra:
        lines += extra + [""]
    if pk.get("made_with", False):
        lines.append("Made with docuframe")
    desc = "\n".join(lines).strip() + "\n"
    (yt / "description.txt").write_text(desc, encoding="utf-8")
    (yt / "tags.txt").write_text(", ".join(pk.get("tags", [])) + "\n", encoding="utf-8")

    checklist = ["# Upload checklist", "",
                 "- [ ] Title: pick one from titles.txt (or write your own)",
                 "- [ ] Description: paste description.txt (sources and credits are required by the image licences)",
                 "- [ ] Subtitles: upload out/captions.srt",
                 "- [ ] Thumbnail: pick one of thumb_1..3.jpg, or design your own from it"]
    if synthetic_voice:
        checklist.append("- [ ] Altered or synthetic content: a synthetic narrator over code-drawn graphics is usually *not* "
                         "realistic content that needs the label; answer **Yes** if the film shows realistic generated people, "
                         "places or events, or a cloned real voice (YouTube rules, checked 2026-11-20)")
    checklist += ["- [ ] Variation: if this is part of a series, check docuframe series report — YouTube does not monetise "
                  "channels whose videos look template-made"]
    (yt / "upload-checklist.md").write_text("\n".join(checklist) + "\n", encoding="utf-8")

    outputs = {}
    for p in sorted((proj / "out").glob("*.mp4")) + [proj / "out" / "captions.srt", proj / "out" / "captions.vtt"]:
        if p.exists() and ".part" not in p.name:
            outputs[str(p.relative_to(proj))] = {"bytes": p.stat().st_size, "sha256_16": sha(p)}
    from .fonts import manifest_entries
    manifest = {
        "docuframe": __version__, "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "project": proj.name, "style": st["name"], "format": fmt, "duration_s": round(b.doc.duration, 2),
        "platform": f"{platform.system()} {platform.release()} / Python {platform.python_version()}",
        "inputs": {k: sha(proj / k) for k in ("script.json", "facts.json", "film.json", "photos.json") if (proj / k).exists()},
        "voice": voice, "timing": b.doc.timing.get("alignment", {"method": "letter-share estimate"}),
        "sources": srcs, "images": [p for p in photos.get("photos", []) if p["id"] in used],
        "fonts": manifest_entries(fonts_used),
        "attribution_lines": credits + (["Fonts: " + ", ".join(fonts_used) + " (open font licences)"] if fonts_used else []),
        "approvals": json.loads((proj / "approvals.json").read_text(encoding="utf-8")) if (proj / "approvals.json").exists() else [],
        "chapters": [{"t": round(t, 2), "title": n} for t, n in chapters],
        "outputs": outputs, "thumbnails": thumbs,
        "rerender": f"docuframe make --project {proj.name} --yes",
        "ownership": "Everything in this film made by docuframe belongs to you and may be used commercially, "
                     "subject only to the attribution lines above.",
    }
    (proj / "out" / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"package: out/youtube/ (titles, description, tags, {len(thumbs)} thumbnails, upload checklist) + out/manifest.json")
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    a = ap.parse_args(argv)
    build(pathlib.Path(a.project).resolve())

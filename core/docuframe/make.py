"""Run every step after the plan, in order, skipping what is already done.

  docuframe make --project P            # stops at the approval stills (director mode)
  docuframe make --project P --yes      # quick mode: no stop (the agent still reviews the stills)
  docuframe make --project P --from render

Steps: voice → narration → align (if installed) → assets → stills → [approval] → render → captions
→ check → package. Approval is recorded in approvals.json (who approved what, when), which the
manifest keeps: proof of human creative direction if a platform ever asks.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import pathlib
import time

STEPS = ["voice", "narration", "align", "assets", "stills", "approve", "render", "captions", "check", "package"]


def done(proj, step):
    a = proj / "audio"
    return {
        "voice": (a / "segments.json").exists() and any((a / "lines").glob("seg*.wav")) if (a / "lines").exists() else False,
        "narration": (a / "timing.json").exists() and (a / "narration.m4a").exists(),
        "align": (a / "timing.json").exists() and "alignment" in json.loads((a / "timing.json").read_text(encoding="utf-8")),
    }.get(step, False)


def approved(proj, what="stills"):
    p = proj / "approvals.json"
    return p.exists() and any(x.get("what") == what for x in json.loads(p.read_text(encoding="utf-8")))


def approve(proj, what, by="user", note=""):
    p = proj / "approvals.json"
    items = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    items.append({"what": what, "by": by, "note": note, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
    p.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--yes", action="store_true", help="quick mode: don't stop for approval")
    ap.add_argument("--approve", action="store_true", help="record that the user approved the stills, then continue")
    ap.add_argument("--from", dest="start", default=None, choices=STEPS)
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    p = str(proj)
    if a.approve:
        approve(proj, "stills", note="approved approval stills")
    steps = STEPS[STEPS.index(a.start):] if a.start else STEPS
    t0 = time.time()
    for step in steps:
        if step in ("voice", "narration") and done(proj, step) and not a.start:
            print(f"[{step}] already done"); continue
        print(f"\n[{step}]", flush=True)
        if step == "voice":
            importlib.import_module("docuframe.voice").main(["--project", p])
        elif step == "narration":
            importlib.import_module("docuframe.narration").main(["--project", p])
        elif step == "align":
            try:
                import faster_whisper  # noqa: F401
            except ImportError:
                print("skipped (optional; word times estimated)"); continue
            if not done(proj, "align"):
                importlib.import_module("docuframe.align").main(["--project", p])
        elif step == "assets":
            if (proj / "photos.json").exists():
                importlib.import_module("docuframe.assets").main(["--project", p])
            if (proj / "map.json").exists():          # map data for map beats (Natural Earth, built once)
                importlib.import_module("docuframe.maps").main(["--project", p])
        elif step == "stills":
            importlib.import_module("docuframe.render").main(["--project", p, "--stills", "auto"])
        elif step == "approve":
            if a.yes:
                approve(proj, "stills", by="quick-mode", note="quick mode: agent reviewed stills, user did not stop the run")
            elif not approved(proj):
                print("Approval stills are in out/stills/ (sheet_*.jpg). Show them to the user.\n"
                      f"When approved: docuframe make --project {proj.name} --approve")
                return
        elif step == "render":
            importlib.import_module("docuframe.render").main(["--project", p] + (["--draft"] if a.draft else []))
        elif step == "captions":
            importlib.import_module("docuframe.captions_cmd").main(["--project", p])
        elif step == "check":
            try:
                importlib.import_module("docuframe.verify").main(["--project", p])
            except SystemExit as e:
                if e.code:
                    print("check found problems (see out/check.md); packaging anyway so you can review")
        elif step == "package":
            importlib.import_module("docuframe.package").main(["--project", p])
    print(f"\ndone in {int(time.time() - t0)} s — film, captions, YouTube package and manifest are in {proj / 'out'}")

"""docuframe command line. Every step is a subcommand; the skill's agent runs them in order.

  docuframe doctor [--fix]          check this machine, print exact fix commands
  docuframe new NAME [--template T] start a project from a worked template
  docuframe styles                  list style packs
  docuframe voice   --project P     narration (local voice, system voice, or your recording)
  docuframe narration --project P   assemble lines into one track + timing.json
  docuframe align   --project P     word-level timing (optional, improves hits and captions)
  docuframe assets  --project P     grade photos, make board textures
  docuframe archive --project P     fetch openly licensed photos listed in photos.json, with credits
  docuframe map     --project P     build map data listed in map.json
  docuframe render  --project P     stills for approval, or the film (chunked, resumable)
  docuframe sfx / mix --project P   sound effects from the film's cues; final mix
  docuframe captions --project P    SRT + VTT (and burned-in captions with --burn)
  docuframe check   --project P     self-review: timing, legibility, safe areas, sources, licences
  docuframe package --project P     YouTube package + manifest.json
  docuframe shorts  --project P     9:16 cut-downs from the same project
  docuframe share   --project P     preview clip + ready-to-post caption
  docuframe make    --project P     run every step after the plan (voice → package)
"""
from __future__ import annotations

import importlib
import sys

COMMANDS = {
    "doctor": "doctor", "new": "project", "styles": "project", "voice": "voice", "split": "voice_split",
    "narration": "narration", "align": "align", "assets": "assets", "archive": "archive", "map": "maps",
    "render": "render", "sfx": "sound", "mix": "sound", "captions": "captions_cmd", "burn": "burn", "check": "verify",
    "package": "package", "shorts": "shorts", "share": "share", "make": "make",
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if sys.platform == "win32":
        for s in (sys.stdout, sys.stderr):
            try:
                s.reconfigure(encoding="utf-8")
            except Exception:
                pass
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if argv[0] in ("--version", "version"):
        from . import __version__
        print(__version__)
        return 0
    cmd = argv.pop(0)
    if cmd not in COMMANDS:
        print(f"unknown command {cmd!r}\n{__doc__}")
        return 2
    mod = importlib.import_module(f"docuframe.{COMMANDS[cmd]}")
    fn = getattr(mod, f"main_{cmd}", None) or mod.main
    try:
        fn(argv)
    except KeyboardInterrupt:
        print("\nstopped. Run the same command again to continue where it left off.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())

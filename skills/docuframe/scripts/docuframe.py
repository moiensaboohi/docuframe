#!/usr/bin/env python3
"""Run docuframe from the skill folder: python scripts/docuframe.py <command> ...

Finds the engine in this order: an installed `docuframe` package, the repo's core/ folder next to
this skill (a git checkout), or the copy bundled in the release zip (scripts/core). It never
downloads or installs anything by itself: if the engine is missing it prints the one command to run.
A skill installed with `npx skills add` has only this folder, so that command installs the engine
(and its Python dependencies) straight from the project's GitHub archive; no git needed.
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
os.environ.setdefault("DOCUFRAME_STYLES", str(SKILL / "styles"))
os.environ.setdefault("DOCUFRAME_TEMPLATES", str(SKILL / "templates"))

for cand in (SKILL.parent.parent / "core", HERE / "core"):
    if (cand / "docuframe" / "cli.py").exists():
        sys.path.insert(0, str(cand))
        break

ENGINE = "https://github.com/moiensaboohi/docuframe/archive/refs/heads/main.zip"

try:
    from docuframe.cli import main
except ImportError as e:
    missing = getattr(e, "name", "") or str(e)
    if missing == "docuframe" or missing.startswith("docuframe"):
        print("The docuframe engine is not installed yet (the skill folder holds the instructions, styles and templates).\n"
              "Run this once (about 150 MB of Python packages), then try again:\n\n"
              f'  "{sys.executable}" -m pip install "docuframe[voice] @ {ENGINE}"\n')
    else:
        print(f"docuframe needs a Python package that is not installed ({missing}).\n"
              f"Run this once, then try again:\n\n"
              f'  "{sys.executable}" -m pip install skia-python numpy pillow fonttools\n\n'
              f"(Optional local voice: add kokoro-onnx soundfile. Optional word timing: add faster-whisper.)")
    sys.exit(1)

sys.exit(main())

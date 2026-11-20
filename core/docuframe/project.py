"""Projects and style packs.

  docuframe new my-film                         # from the default template
  docuframe new my-film --template explainer    # docuframe new --list shows templates
  docuframe styles                              # every style pack, one line each
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil

from . import styles as S


def template_dirs():
    out = []
    if os.environ.get("DOCUFRAME_TEMPLATES"):
        out += [pathlib.Path(p) for p in os.environ["DOCUFRAME_TEMPLATES"].split(os.pathsep)]
    out.append(S.REPO / "skills" / "docuframe" / "templates")
    return [p for p in out if p.exists()]


def templates():
    found = {}
    for root in reversed(template_dirs()):
        for d in root.iterdir():
            if (d / "film.json").exists():
                found[d.name] = d
    return dict(sorted(found.items()))


def main_new(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", nargs="?")
    ap.add_argument("--template", default="history-short")
    ap.add_argument("--style", default=None)
    ap.add_argument("--format", default=None)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    t = templates()
    if a.list or not a.name:
        for n, d in t.items():
            plan = json.loads((d / "film.json").read_text(encoding="utf-8"))
            print(f"{n:<22} style {plan.get('style')}, {plan.get('format', '16:9')}")
        return
    if a.template not in t:
        raise SystemExit(f"template {a.template!r} not found. Templates: {', '.join(t)}")
    dst = pathlib.Path(a.name).resolve()
    if dst.exists() and any(dst.iterdir()):
        raise SystemExit(f"{dst} already exists and is not empty. Pick another name.")
    shutil.copytree(t[a.template], dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("out", "audio", "assets", "*.md"))
    plan = json.loads((dst / "film.json").read_text(encoding="utf-8"))
    if a.style:
        plan["style"] = a.style
    if a.format:
        plan["format"] = a.format
    (dst / "film.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"new project {dst} from template {a.template!r} (style {plan['style']}).\n"
          f"Edit script.json, facts.json, film.json and photos.json, then: docuframe make --project {dst.name}")


def main_styles(argv=None):
    for name, d in S.available(None).items():
        st = json.loads((d / "style.json").read_text(encoding="utf-8"))
        print(f"{name:<22} {st.get('label', '')} — {st.get('summary', '')[:90]}")


main = main_new

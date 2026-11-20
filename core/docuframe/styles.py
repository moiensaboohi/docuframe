"""Style packs: data, not code.

A style is a folder with style.json (tokens and scene defaults), rules.md (what the style is for and
how to judge it) and reference stills. The engine never branches on a style's name, so a community
pack needs no engine change.

Search order for a style named N:
  1. <project>/styles/N            (a channel's own copy)
  2. $DOCUFRAME_STYLES/N           (set by the skill launcher to the skill's styles folder)
  3. <repo>/skills/docuframe/styles/N, <repo>/community-styles/N   (repo checkout / editable install)
"""
from __future__ import annotations

import copy
import json
import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent

DEFAULTS = {
    "camera": "world",                       # "world" (one continuous camera) or "cuts" (scene by scene)
    "tokens": {
        "color": {"bg": [12, 9, 7], "ink": [40, 30, 22], "paper": [246, 243, 236], "accent": [168, 28, 24],
                  "highlight": [246, 206, 46], "text": [246, 243, 236], "muted": [150, 140, 128], "label": [176, 24, 20]},
        "font": {"title": ["Oswald"], "body": ["Libre Baskerville"], "mono": ["Courier Prime"],
                 "hand": ["Homemade Apple"], "label": ["Montserrat"]},
    },
    "finish": {"board": "cork_dark.png", "bg": [12, 9, 7], "grade": [1.015, 1.0, 0.975], "grain": 0.026,
               "glow": 0.24, "vignette": 0.75, "curve": 0.25, "dim": [6, 4, 3]},
    "map_look": "period",
    "photo_grade": "bw",
    "captions": "clean",
    "pacing": {"visual_change_s": [4, 8], "interrupt_s": [30, 60], "hook_s": 10},
    "layout": {"spacing": 5200, "row": 4, "jitter_deg": 3.0},
    "scenes": {},
}

# font token -> engine role
ROLE_OF = {"title": "cond", "body": "serif", "mono": "mono", "hand": "hand", "label": "label"}


def search_paths(project: pathlib.Path | None = None) -> list[pathlib.Path]:
    out = []
    if project:
        out.append(pathlib.Path(project) / "styles")
    if os.environ.get("DOCUFRAME_STYLES"):
        out += [pathlib.Path(p) for p in os.environ["DOCUFRAME_STYLES"].split(os.pathsep)]
    out += [REPO / "skills" / "docuframe" / "styles", REPO / "community-styles"]
    return [p for p in out if p.exists()]


def available(project=None) -> dict[str, pathlib.Path]:
    found = {}
    for root in reversed(search_paths(project)):
        for d in root.iterdir():
            if (d / "style.json").exists():
                found[d.name] = d
    return dict(sorted(found.items()))


def _merge(a, b):
    out = copy.deepcopy(a)
    for k, v in b.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def load(name: str, project=None, channel: dict | None = None) -> dict:
    """Style dict: defaults <- style.json <- channel style file overrides (colours, fonts, pacing)."""
    styles = available(project)
    if name not in styles:
        raise SystemExit(f"style {name!r} not found. Available: {', '.join(styles) or 'none (is the skill installed?)'}")
    data = json.loads((styles[name] / "style.json").read_text(encoding="utf-8"))
    st = _merge(DEFAULTS, data)
    if channel:
        st = _merge(st, {k: v for k, v in channel.items() if k in ("tokens", "finish", "pacing", "captions", "scenes")})
    st["name"] = name
    st["dir"] = str(styles[name])
    return st


def roles(style: dict) -> dict[str, list[str]]:
    from .engine import FONT_ROLES
    out = {}
    for tok, role in ROLE_OF.items():
        out[role] = list(style["tokens"]["font"].get(tok, [])) + FONT_ROLES.get(role, [])
    out["labelm"] = out["label"]
    return out


def rgb(style: dict, key: str, default=(0, 0, 0)):
    return tuple(style["tokens"]["color"].get(key, default))

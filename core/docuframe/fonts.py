"""Fonts: a small registry of openly licensed faces, fetched on first use into a per-user cache.

Why fetch instead of bundling: full script coverage (Arabic, Persian, Urdu, Hebrew, Devanagari,
Bengali, Tamil, Chinese, Japanese, Korean) is tens of megabytes, and most films need two or three
faces. Every face here is SIL OFL 1.1; its licence text is saved next to it and listed in the
film's manifest, so the user always knows what is in their video.

Sources are the upstream font repositories on GitHub (raw files). Nothing else is downloaded.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import time
import urllib.request

GF = "https://raw.githubusercontent.com/google/fonts/main/ofl"
GFA = "https://raw.githubusercontent.com/google/fonts/main/apache"
NOTO = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts"
VAZIR = "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master"

# name -> file url, licence url. SIL OFL 1.1 unless "spdx" says otherwise (checked 2026-11-20).
REGISTRY: dict[str, dict] = {
    # Latin display and text faces used by the styles
    "Oswald": {"url": f"{GF}/oswald/Oswald%5Bwght%5D.ttf", "licence": f"{GF}/oswald/OFL.txt"},
    "Libre Baskerville": {"url": f"{GF}/librebaskerville/LibreBaskerville%5Bwght%5D.ttf", "licence": f"{GF}/librebaskerville/OFL.txt"},
    "Courier Prime": {"url": f"{GF}/courierprime/CourierPrime-Bold.ttf", "licence": f"{GF}/courierprime/OFL.txt"},
    "Homemade Apple": {"url": f"{GFA}/homemadeapple/HomemadeApple-Regular.ttf", "licence": f"{GFA}/homemadeapple/LICENSE.txt", "spdx": "Apache-2.0"},
    "Montserrat": {"url": f"{GF}/montserrat/Montserrat%5Bwght%5D.ttf", "licence": f"{GF}/montserrat/OFL.txt"},
    "Inter": {"url": f"{GF}/inter/Inter%5Bopsz,wght%5D.ttf", "licence": f"{GF}/inter/OFL.txt"},
    "Space Mono": {"url": f"{GF}/spacemono/SpaceMono-Bold.ttf", "licence": f"{GF}/spacemono/OFL.txt"},
    "Playfair Display": {"url": f"{GF}/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf", "licence": f"{GF}/playfairdisplay/OFL.txt"},
    "Special Elite": {"url": f"{GFA}/specialelite/SpecialElite-Regular.ttf", "licence": f"{GFA}/specialelite/LICENSE.txt", "spdx": "Apache-2.0"},
    # Script coverage
    "Noto Sans": {"url": f"{NOTO}/NotoSans/hinted/ttf/NotoSans-Regular.ttf", "licence": f"{GF}/notosans/OFL.txt"},
    "Noto Sans Bold": {"url": f"{NOTO}/NotoSans/hinted/ttf/NotoSans-Bold.ttf", "licence": f"{GF}/notosans/OFL.txt"},
    "Noto Sans Arabic": {"url": f"{NOTO}/NotoSansArabic/hinted/ttf/NotoSansArabic-Bold.ttf", "licence": f"{GF}/notosansarabic/OFL.txt"},
    "Vazirmatn": {"url": f"{VAZIR}/fonts/ttf/Vazirmatn-Bold.ttf", "licence": f"{VAZIR}/OFL.txt"},
    "Noto Nastaliq Urdu": {"url": f"{GF}/notonastaliqurdu/NotoNastaliqUrdu%5Bwght%5D.ttf", "licence": f"{GF}/notonastaliqurdu/OFL.txt"},
    "Noto Sans Hebrew": {"url": f"{NOTO}/NotoSansHebrew/hinted/ttf/NotoSansHebrew-Bold.ttf", "licence": f"{GF}/notosanshebrew/OFL.txt"},
    "Noto Sans Devanagari": {"url": f"{NOTO}/NotoSansDevanagari/hinted/ttf/NotoSansDevanagari-Bold.ttf", "licence": f"{GF}/notosansdevanagari/OFL.txt"},
    "Noto Sans Bengali": {"url": f"{NOTO}/NotoSansBengali/hinted/ttf/NotoSansBengali-Bold.ttf", "licence": f"{GF}/notosansbengali/OFL.txt"},
    "Noto Sans Tamil": {"url": f"{NOTO}/NotoSansTamil/hinted/ttf/NotoSansTamil-Bold.ttf", "licence": f"{GF}/notosanstamil/OFL.txt"},
    "Noto Sans Thai": {"url": f"{NOTO}/NotoSansThai/hinted/ttf/NotoSansThai-Bold.ttf", "licence": f"{GF}/notosansthai/OFL.txt"},
    "Noto Sans SC": {"url": f"{GF}/notosanssc/NotoSansSC%5Bwght%5D.ttf", "licence": f"{GF}/notosanssc/OFL.txt"},
    "Noto Sans JP": {"url": f"{GF}/notosansjp/NotoSansJP%5Bwght%5D.ttf", "licence": f"{GF}/notosansjp/OFL.txt"},
    "Noto Sans KR": {"url": f"{GF}/notosanskr/NotoSansKR%5Bwght%5D.ttf", "licence": f"{GF}/notosanskr/OFL.txt"},
}

# script -> fallback face (language can override, see face_for_script)
SCRIPT_FACE = {
    "latin": "Noto Sans Bold", "arab": "Noto Sans Arabic", "hebr": "Noto Sans Hebrew",
    "deva": "Noto Sans Devanagari", "beng": "Noto Sans Bengali", "taml": "Noto Sans Tamil",
    "thai": "Noto Sans Thai", "hani": "Noto Sans SC", "jpan": "Noto Sans JP", "hang": "Noto Sans KR",
}
LANG_FACE = {"fa": "Vazirmatn", "ur": "Noto Nastaliq Urdu", "ja": "Noto Sans JP", "ko": "Noto Sans KR",
             "zh": "Noto Sans SC", "ar": "Noto Sans Arabic", "he": "Noto Sans Hebrew", "hi": "Noto Sans Devanagari",
             "bn": "Noto Sans Bengali", "ta": "Noto Sans Tamil"}

RTL_SCRIPTS = {"arab", "hebr"}


def cache_dir() -> pathlib.Path:
    """Per-user font cache. DOCUFRAME_HOME overrides (useful in CI and Codespaces)."""
    base = os.environ.get("DOCUFRAME_HOME")
    if base:
        root = pathlib.Path(base)
    elif sys.platform == "win32":
        root = pathlib.Path(os.environ.get("LOCALAPPDATA") or pathlib.Path.home() / "AppData" / "Local") / "docuframe"
    elif sys.platform == "darwin":
        root = pathlib.Path.home() / "Library" / "Caches" / "docuframe"
    else:
        root = pathlib.Path(os.environ.get("XDG_CACHE_HOME") or pathlib.Path.home() / ".cache") / "docuframe"
    d = root / "fonts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _file_name(name: str) -> str:
    return name.replace(" ", "") + ".ttf"


def _download(url: str, dst: pathlib.Path, tries: int = 3) -> None:
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "docuframe-fonts/1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            fd, tmp = tempfile.mkstemp(dir=dst.parent, suffix=".part")
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            replace_with_retry(pathlib.Path(tmp), dst)
            return
        except Exception as e:  # network blips, Windows file locks
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"could not download {url}: {last}")


def replace_with_retry(src: pathlib.Path, dst: pathlib.Path, tries: int = 10) -> None:
    """os.replace, retried: on Windows an antivirus scan or an open preview briefly locks new files."""
    for i in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            time.sleep(0.2 * (i + 1))
    os.replace(src, dst)


def path(name: str, fetch: bool = True) -> pathlib.Path | None:
    """Local path of a registry face, downloading it (and its licence) if allowed."""
    if name not in REGISTRY:
        return None
    d = cache_dir()
    p = d / _file_name(name)
    if p.exists() and p.stat().st_size > 1000:
        return p
    if not fetch or os.environ.get("DOCUFRAME_OFFLINE"):
        return None
    ent = REGISTRY[name]
    _download(ent["url"], p)
    lic = d / (_file_name(name)[:-4] + ".LICENSE.txt")
    if not lic.exists():
        try:
            _download(ent["licence"], lic)
        except RuntimeError:
            lic.write_text(f"SIL Open Font License 1.1 — see {ent['licence']}\n", encoding="utf-8")
    return p


def static_instance(name: str, weight: int, fetch: bool = True) -> pathlib.Path | None:
    """A static file of a variable font at one weight (variable fonts default to their thinnest
    instance in most renderers). Made once with fontTools' instancer and cached."""
    src = path(name, fetch)
    if src is None:
        return None
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return src
    dst = src.with_name(f"{src.stem}-w{weight}.ttf")
    if dst.exists():
        return dst
    f = TTFont(str(src))
    if "fvar" not in f:
        return src
    axes = {a.axisTag: a for a in f["fvar"].axes}
    loc = {}
    for tag, a in axes.items():
        loc[tag] = max(a.minValue, min(a.maxValue, weight)) if tag == "wght" else a.defaultValue
    from fontTools.varLib import instancer
    inst = instancer.instantiateVariableFont(f, loc, updateFontNames=False)
    fd, tmp = tempfile.mkstemp(dir=dst.parent, suffix=".part")
    os.close(fd)
    inst.save(tmp)
    replace_with_retry(pathlib.Path(tmp), dst)
    return dst


def detect_scripts(text: str) -> set[str]:
    """Scripts present in a string (coarse Unicode blocks; enough to pick fonts and direction)."""
    out = set()
    for ch in text:
        o = ord(ch)
        if o < 0x0250 or 0x1E00 <= o < 0x1F00:
            if ch.isalpha():
                out.add("latin")
        elif 0x0590 <= o < 0x0600 or 0xFB1D <= o < 0xFB50:
            out.add("hebr")
        elif 0x0600 <= o < 0x0780 or 0x0860 <= o < 0x08FF or 0xFB50 <= o < 0xFE00 or 0xFE70 <= o < 0xFF00:
            out.add("arab")
        elif 0x0900 <= o < 0x0980:
            out.add("deva")
        elif 0x0980 <= o < 0x0A00:
            out.add("beng")
        elif 0x0B80 <= o < 0x0C00:
            out.add("taml")
        elif 0x0E00 <= o < 0x0E80:
            out.add("thai")
        elif 0x3040 <= o < 0x3100 or 0x31F0 <= o < 0x3200:
            out.add("jpan")
        elif 0xAC00 <= o < 0xD7B0 or 0x1100 <= o < 0x1200:
            out.add("hang")
        elif 0x4E00 <= o < 0xA000 or 0x3400 <= o < 0x4DC0 or 0x3000 <= o < 0x3040 or 0xFF00 <= o < 0xFFF0:
            out.add("hani")
    if "jpan" in out:
        out.discard("hani")
    return out


def is_rtl(text: str) -> bool:
    """Base direction of a string: RTL if its first strong letter is Arabic or Hebrew."""
    for ch in text:
        s = detect_scripts(ch)
        if s:
            return bool(s & RTL_SCRIPTS)
    return False


def faces_for(text: str, lang: str | None = None) -> list[str]:
    """Fallback faces a string needs beyond its style face, most specific first."""
    faces = []
    if lang and lang.split("-")[0] in LANG_FACE:
        faces.append(LANG_FACE[lang.split("-")[0]])
    for s in sorted(detect_scripts(text) - {"latin"}):     # Latin is covered by the style's own faces
        f = SCRIPT_FACE.get(s)
        if f and f not in faces:
            faces.append(f)
    return faces


def manifest_entries(names) -> list[dict]:
    return [{"font": n, "licence": REGISTRY[n].get("spdx", "SIL OFL 1.1"), "source": REGISTRY[n]["url"], "licence_text": REGISTRY[n]["licence"]}
            for n in sorted(set(names)) if n in REGISTRY]


if __name__ == "__main__":  # python -m docuframe.fonts Oswald "Noto Sans Arabic" ...
    for n in sys.argv[1:] or ["Oswald"]:
        print(n, "->", path(n))
    print(json.dumps(manifest_entries(sys.argv[1:]), indent=1))

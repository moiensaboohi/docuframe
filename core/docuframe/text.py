"""Shaped text for every script.

All on-screen text goes through Skia's paragraph layout (HarfBuzz shaping + ICU bidi), so Arabic and
Persian letters join, mixed right-to-left / left-to-right runs order correctly, and Indic conjuncts
form. A plain per-glyph drawString does none of that: it is what makes Arabic come out as isolated,
reversed letters in many tools.

The Python binding does not expose a paragraph's base direction, so right-to-left strings are wrapped
in Unicode isolates (RLI ... PDI); bidi then resolves them as a right-to-left paragraph.

Reveal (type-on) works two ways: for simple left-to-right text it shapes the first n characters (a
typewriter); for anything shaped (joined scripts, conjuncts, RTL) it wipes a clip in reading order,
so letters are never shown in a half-joined or reordered state.
"""
from __future__ import annotations

import pathlib

import skia

from . import fonts as F

RLI, PDI = "⁧", "⁩"
ROLE_WEIGHT = {"cond": 600, "label": 700, "labelm": 500, "serif": 400, "mono": 700, "hand": 400, "display": 700, "body": 500}


def _tag(s: str) -> int:
    return (ord(s[0]) << 24) | (ord(s[1]) << 16) | (ord(s[2]) << 8) | ord(s[3])


class FontBook:
    """Typefaces by role plus script fallbacks, registered into one FontCollection."""

    def __init__(self, roles: dict[str, list] | None = None, project_fonts: pathlib.Path | None = None,
                 lang: str | None = None, fetch: bool = True):
        self.roles = roles or {}
        self.project_fonts = pathlib.Path(project_fonts) if project_fonts else None
        self.lang = lang
        self.fetch = fetch
        self.provider = skia.textlayout.TypefaceFontProvider()
        self.collection = skia.textlayout.FontCollection()
        self.collection.setDefaultFontManager(self.provider)
        self.family_of_role: dict[str, str] = {}
        self.loaded: set[str] = set()       # registry faces actually used (for the manifest)
        self.system = skia.FontMgr.RefDefault()
        self.unicode = skia.Unicode.ICU_Make()
        self._para_cache: dict = {}
        self._fallback_families: dict[str, list[str]] = {}
        self.notes: list[str] = []

    # -- loading
    def _register_file(self, p: pathlib.Path, alias: str | None = None) -> str | None:
        tf = skia.Typeface.MakeFromFile(str(p))
        if tf is None:
            return None
        if alias:
            self.provider.registerTypeface(tf, alias)
            return alias
        self.provider.registerTypeface(tf)
        return tf.getFamilyName()

    def _registry_family(self, name: str, weight: int | None = None) -> str | None:
        p = F.static_instance(name, weight or 400, fetch=self.fetch)
        if p is None:
            return None
        alias = name if weight is None else f"{name}@{weight}"
        fam = self._register_file(p, alias=alias)
        if fam:
            self.loaded.add(name)
        return fam

    def role_family(self, role: str) -> str:
        """Family name for a style role (project file > style choice from registry > system > default)."""
        if role in self.family_of_role:
            return self.family_of_role[role]
        fam = None
        if self.project_fonts:
            for ext in (".ttf", ".otf"):
                p = self.project_fonts / f"{role}{ext}"
                if p.exists():
                    fam = self._register_file(p, alias=f"project-{role}")
                    break
        for cand in self.roles.get(role, []) if fam is None else []:
            name = cand if isinstance(cand, str) else cand[0]
            weight = ROLE_WEIGHT.get(role)
            if ":" in name:                      # "Inter:800" picks a weight of a variable face
                name, w = name.rsplit(":", 1)
                weight = int(w)
            if name in F.REGISTRY:
                try:
                    fam = self._registry_family(name, weight)
                except RuntimeError as e:
                    self.notes.append(f"font {name}: {e}")
                    fam = None
            else:
                tf = self.system.matchFamilyStyle(name, skia.FontStyle.Bold() if role in ("cond", "label", "mono") else skia.FontStyle.Normal())
                if tf is not None and tf.getFamilyName().lower() == name.lower():
                    self.provider.registerTypeface(tf, f"sys-{name}")
                    fam = f"sys-{name}"
            if fam:
                break
        if fam is None:
            tf = self.system.legacyMakeTypeface("", skia.FontStyle.Bold() if role in ("cond", "label", "mono") else skia.FontStyle.Normal())
            if tf is not None:
                self.provider.registerTypeface(tf, "sys-default")
                fam = "sys-default"
                self.notes.append(f"role {role!r}: no style font available, using the system default")
            else:
                fam = "sys-default"
        self.family_of_role[role] = fam
        return fam

    def families(self, role: str, text: str) -> list[str]:
        key = (role, frozenset(F.detect_scripts(text)))
        if key not in self._fallback_families:
            fams = [self.role_family(role)]
            for face in F.faces_for(text, self.lang):
                try:
                    f = self._registry_family(face, 700) if face not in self.loaded else f"{face}@700"
                except RuntimeError as e:
                    self.notes.append(f"font {face}: {e}")
                    f = None
                if f and f not in fams:
                    fams.append(f)
            self._fallback_families[key] = fams
        return self._fallback_families[key]

    # -- layout
    def paragraph(self, text: str, size: float, role: str, rgb=(0, 0, 0), track: float = 0.0,
                  width: float = 1e6, align: str = "left", leading: float | None = None) -> skia.textlayout.Paragraph:
        rtl = F.is_rtl(text)
        shaped = rtl or bool(F.detect_scripts(text) - {"latin"})
        key = (text, round(size, 2), role, tuple(rgb), round(track, 4), round(width), align, leading)
        p = self._para_cache.get(key)
        if p is not None:
            return p
        ps = skia.textlayout.ParagraphStyle()
        al = {"left": skia.textlayout.TextAlign.kLeft, "right": skia.textlayout.TextAlign.kRight,
              "center": skia.textlayout.TextAlign.kCenter}[align]
        ps.setTextAlign(al)
        ts = skia.textlayout.TextStyle()
        ts.setFontFamilies(self.families(role, text))
        ts.setFontSize(size)
        ts.setForegroundPaint(skia.Paint(AntiAlias=True, Color=skia.Color(int(rgb[0]), int(rgb[1]), int(rgb[2]))))
        if track and not shaped:      # tracking breaks joined scripts; only for simple text
            ts.setLetterSpacing(track * size)
        if self.lang:
            ts.setLocale(self.lang)
        if leading:                   # tight display leading (line height as a multiple of size)
            ts.setHeightOverride(True)
            ts.setHeight(leading)
        ps.setTextStyle(ts)
        b = skia.textlayout.ParagraphBuilder.make(ps, self.collection, self.unicode)
        b.pushStyle(ts)
        b.addText(f"{RLI}{text}{PDI}" if rtl else text)
        p = b.Build()
        p.layout(width)
        if len(self._para_cache) > 4000:
            self._para_cache.clear()
        self._para_cache[key] = p
        return p

    def width(self, text: str, size: float, role: str, track: float = 0.0) -> float:
        if not text:
            return 0.0
        return self.paragraph(text, size, role, track=track).MaxIntrinsicWidth

    def draw(self, c: skia.Canvas, text: str, x: float, y: float, size: float, role: str, rgb, a: float = 1.0,
             track: float = 0.0, align: str = "left", reveal: float | None = None) -> float:
        """Draw one line with its baseline at y. align positions the line around x. Returns its width."""
        if not text or a <= 0:
            return self.width(text, size, role, track) if text else 0.0
        rtl = F.is_rtl(text)
        shaped = rtl or bool(F.detect_scripts(text) - {"latin"})
        full = self.paragraph(text, size, role, rgb, track)
        w = full.MaxIntrinsicWidth
        x0 = x - w / 2 if align == "center" else x - w if align == "right" else x
        n = len(text) if reveal is None else max(0, min(len(text), reveal))
        if n <= 0:
            return w
        para = full
        clip = None
        if n < len(text):
            if shaped:
                frac = n / len(text)
                h = full.Height
                top = y - full.AlphabeticBaseline
                clip = (skia.Rect.MakeLTRB(x0 + w * (1 - frac), top - h, x0 + w + 2, top + 2 * h) if rtl
                        else skia.Rect.MakeLTRB(x0 - 2, top - h, x0 + w * frac, top + 2 * h))
            else:
                para = self.paragraph(text[:int(n)], size, role, rgb, track)
        top = y - para.AlphabeticBaseline
        layer = a < 0.999
        if layer:
            c.saveLayerAlpha(skia.Rect.MakeLTRB(x0 - size, top - size, x0 + w + size, top + para.Height + size), int(255 * a))
        else:
            c.save()
        if clip is not None:
            c.clipRect(clip)
        # the paragraph is left-aligned and LTR at its base; an RTL string sits inside it as one
        # isolate, so its visual line still starts at x0
        para.paint(c, x0, top)
        c.restore()
        return w

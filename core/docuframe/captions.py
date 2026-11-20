"""Caption text and timing: tokens, word times, sentence-sized cues, and the burned-in caption painter.

Cue text is always the script's display text; word times come from alignment when available, else
from each word's share of the line's letters. Scripts written without spaces (Chinese, Japanese,
Thai) are tokenised per character and joined without spaces.

Burned-in styles (for shorts and social clips):
  clean        sentence case, soft shadow, bottom gradient
  highlighter  bold caps; the word being spoken gets a yellow marker behind it
  bar          white text on a solid colour bar
"""
from __future__ import annotations

import numpy as np
import skia

from .fonts import detect_scripts
from .motion import ease_out, window

UNSPACED = {"hani", "jpan", "thai"}


def _tokens(text):
    if detect_scripts(text) & UNSPACED:
        return [ch for ch in text if not ch.isspace()]
    return text.replace('"', "").split()


def join_tokens(tokens):
    tokens = list(tokens)
    return ("" if detect_scripts("".join(tokens)) & UNSPACED else " ").join(tokens)


def words_with_times(seg):
    """[(display token, start)] for one narration line: aligned starts when the counts agree,
    otherwise each token's share of the line's spoken length (digits count extra: "1919" is long)."""
    shown = _tokens(seg["caption"])
    aligned = seg.get("words") or []
    if len(aligned) == len(shown):
        return [(tok, w["start"]) for tok, w in zip(shown, aligned)]

    def cost(tok):
        digits = sum(ch.isdigit() for ch in tok)
        return max(1, sum(ch.isalpha() for ch in tok) + (3 * digits + 4) * bool(digits))
    costs = [cost(tok) for tok in shown]
    starts = np.concatenate([[0.0], np.cumsum(costs)[:-1]]) / max(1, sum(costs))
    return [(tok, seg["start"] + float(f) * (seg["end"] - seg["start"])) for tok, f in zip(shown, starts)]


MAX_SECONDS, MAX_CHARS = {"clean": 3.2, "highlighter": 1.8, "bar": 2.4}, {"clean": 48, "highlighter": 28, "bar": 34}
STOPS = tuple(".,;:!?،؛。，！？")


def chunks_for(timing, style="clean"):
    """Caption cues: [{'words': [(token, t)], 't0', 't1'}]. A cue closes when it would run longer than
    the style allows on screen or in characters; a natural pause (punctuation) closes it early once it
    is half full. Cues never span two narration lines."""
    max_s, max_c = MAX_SECONDS.get(style, 3.0), MAX_CHARS.get(style, 42)
    out = []
    for seg in timing["segments"]:
        words = words_with_times(seg)
        ends = [t for _, t in words[1:]] + [seg["end"]]
        start = 0
        while start < len(words):
            stop = start
            while stop + 1 < len(words):
                text = join_tokens(w for w, _ in words[start:stop + 2])
                if ends[stop + 1] - words[start][1] > max_s or len(text) > max_c:
                    break
                stop += 1
                if words[stop - 1][0].endswith(STOPS) and len(join_tokens(w for w, _ in words[start:stop])) > max_c / 2:
                    stop -= 1
                    break
            if stop + 1 < len(words):
                pauses = [k for k in range(start, stop) if words[k][0].endswith(STOPS) and k - start >= (stop - start) * 0.4]
                if pauses:                        # end the cue where the narrator pauses
                    stop = pauses[-1]
                elif stop > start and len(words[stop][0]) <= 3:
                    stop -= 1                     # don't leave "a" or "of" hanging at the end of a cue
            out.append({"words": words[start:stop + 1], "t0": words[start][1], "t1": ends[stop]})
            start = stop + 1
        if out:
            out[-1]["t1"] = seg["end"] + 0.25
    return out


class Captions:
    """Paints the caption layer for time t onto a transparent RGBA frame (H, W, 4)."""

    def __init__(self, style, width, height, timing, fonts_dir=None, lang=None):
        from .engine import Res
        self.style, self.W, self.H = style, width, height
        self.k = min(width, height) / 1080.0
        self.res = Res(1.0, None, fonts_dir, lang=lang or timing.get("lang"))
        self.cues = chunks_for(timing, style)
        self.surface = skia.Surface(width, height)

    def cue_at(self, t):
        for c in self.cues:
            if c["t0"] - 0.05 <= t < c["t1"]:
                return c
        return None

    def layer(self, t):
        cue = self.cue_at(t)
        if cue is None:
            return None
        text = join_tokens(w for w, _ in cue["words"])
        tall = self.H > self.W
        size = (54 if tall else 46) * self.k
        y = self.H * (0.68 if tall else 0.9)
        a = window(t, cue["t0"] - 0.05, 0.12)
        book = self.res.book
        with self.surface as c:
            c.clear(skia.ColorTRANSPARENT)
            if self.style == "highlighter":
                text = text.upper() if not detect_scripts(text) - {"latin"} else text
                w = book.width(text, size, "cond")
                x = self.W / 2 - w / 2
                current = [i for i, (_, wt) in enumerate(cue["words"]) if wt <= t]
                if current:
                    i = current[-1]
                    before = join_tokens(w2 for w2, _ in cue["words"][:i])
                    word = cue["words"][i][0]
                    if not detect_scripts(text) - {"latin"}:
                        before, word = before.upper(), word.upper()
                    x0 = x + (book.width(before + " ", size, "cond") if before else 0)
                    ww = book.width(word, size, "cond") * ease_out(window(t, cue["words"][i][1], 0.15))
                    c.drawRect(skia.Rect.MakeXYWH(x0 - 6 * self.k, y - size * 0.95, ww + 12 * self.k, size * 1.2),
                               skia.Paint(Color=skia.Color(246, 206, 46, int(235 * a))))
                book.draw(c, text, self.W / 2 + 2 * self.k, y + 2 * self.k, size, "cond", (0, 0, 0), 0.6 * a, 0, "center")
                book.draw(c, text, self.W / 2, y, size, "cond", (250, 248, 242), a, 0, "center")
            elif self.style == "bar":
                w = book.width(text, size, "label")
                c.drawRect(skia.Rect.MakeXYWH(self.W / 2 - w / 2 - 24 * self.k, y - size * 1.05, w + 48 * self.k, size * 1.45),
                           skia.Paint(Color=skia.Color(176, 24, 20, int(240 * a))))
                book.draw(c, text, self.W / 2, y, size, "label", (255, 255, 255), a, 0, "center")
            else:
                g = skia.GradientShader.MakeLinear([skia.Point(0, self.H * 0.72), skia.Point(0, self.H)],
                                                   [skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, int(150 * a))])
                c.drawRect(skia.Rect.MakeXYWH(0, self.H * 0.72, self.W, self.H * 0.28), skia.Paint(Shader=g))
                book.draw(c, text, self.W / 2 + 2 * self.k, y + 2 * self.k, size, "label", (0, 0, 0), 0.7 * a, 0, "center")
                book.draw(c, text, self.W / 2, y, size, "label", (250, 250, 250), a, 0, "center")
        return self.surface.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)


def composite(frame: np.ndarray, layer: np.ndarray) -> np.ndarray:
    """Premultiplied RGBA layer over an RGB frame."""
    alpha = layer[..., 3:4].astype(np.float32) / 255.0
    return np.clip(frame.astype(np.float32) * (1 - alpha) + layer[..., :3].astype(np.float32), 0, 255).astype(np.uint8)

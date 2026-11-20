"""Sound: effects synthesised from the film's own cues, and the final mix.

  docuframe sfx --project P                 # audio/sfx.wav from the items' cues (nothing downloaded)
  docuframe mix --project P [--music bed.mp3] [--music-gain -20]

Every effect is generated in code from noise and tones, so there is nothing to license. The mix puts
narration on top, ducks the music under the voice, and levels the result to -14 LUFS (streaming level).
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from . import audio as A
from .util import run

R = A.RATE


def _env(n, attack, decay):
    t = np.arange(n) / R
    return np.minimum(1.0, t / max(attack, 1e-4)) * np.exp(-t / max(decay, 1e-4))


def _noise(n, seed):
    return np.random.default_rng(seed).standard_normal(n).astype(np.float32)


def _band(x, lo, hi):
    f = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / R)
    f[(freqs < lo) | (freqs > hi)] = 0
    return np.fft.irfft(f, len(x)).astype(np.float32)


def synth(kind, seed=0, dur=None):
    rnd = np.random.default_rng(seed)
    if kind == "whoosh":
        n = int(R * 0.9)
        x = _band(_noise(n, seed), 300, 4000)
        t = np.linspace(0, 1, n)
        return x * np.sin(np.pi * t) ** 2 * 0.5
    if kind == "impact":
        n = int(R * 0.7)
        t = np.arange(n) / R
        thump = np.sin(2 * np.pi * (55 + 40 * np.exp(-t * 18)) * t) * _env(n, 0.002, 0.18)
        click = _band(_noise(n, seed), 1500, 7000) * _env(n, 0.0005, 0.02) * 0.4
        return (thump + click) * 0.9
    if kind in ("drop", "paper"):
        n = int(R * 0.35)
        x = _band(_noise(n, seed), 800 if kind == "paper" else 400, 6000)
        return x * _env(n, 0.004, 0.06 if kind == "drop" else 0.12) * 0.5
    if kind in ("tick", "type"):
        n = int(R * (dur or 0.05)) if kind == "type" else int(R * 0.05)
        out = np.zeros(max(n, int(R * 0.05)), np.float32)
        hits = [0] if kind == "tick" else list(range(0, len(out) - 800, int(R * rnd.uniform(0.07, 0.11))))
        for h in hits:
            m = min(800, len(out) - h)
            out[h:h + m] += _band(_noise(m, seed + h), 2000, 9000) * _env(m, 0.0003, 0.008)
        return out * 0.6
    if kind in ("pen", "marker", "string", "roll"):
        n = int(R * max(0.2, dur or 0.6))
        lo, hi = {"pen": (2500, 9000), "marker": (900, 5000), "string": (300, 2500), "roll": (1500, 6000)}[kind]
        x = _band(_noise(n, seed), lo, hi)
        t = np.linspace(0, 1, n)
        wob = 0.6 + 0.4 * np.sin(2 * np.pi * rnd.uniform(5, 9) * t * n / R)
        return x * np.sin(np.pi * t) ** 0.6 * wob * (0.18 if kind != "roll" else 0.12)
    if kind == "swell":
        n = int(R * 1.2)
        t = np.arange(n) / R
        x = sum(np.sin(2 * np.pi * f * t) for f in (110, 165, 220)) / 3
        return x * np.sin(np.pi * t / t[-1]) ** 2 * 0.15
    return np.zeros(1, np.float32)


def build_sfx(proj: pathlib.Path):
    from .scenes import build
    film, _, doc, _ = build(proj)
    cues = film.all_cues()
    track = np.zeros(int(R * (doc.duration + 2)), np.float32)
    for i, q in enumerate(cues):
        s = synth(q["type"], seed=i, dur=q.get("dur"))
        a = int(q["t"] * R)
        b = min(len(track), a + len(s))
        if b > a:
            track[a:b] += s[: b - a] * float(q.get("gain", 1.0)) * 0.5
    A.write(proj / "audio" / "sfx.wav", np.tanh(track))
    kinds = {}
    for q in cues:
        kinds[q["type"]] = kinds.get(q["type"], 0) + 1
    (proj / "audio" / "sfx_cues.json").write_text(json.dumps(cues, indent=1), encoding="utf-8")
    print(f"sfx: {len(cues)} cues ({', '.join(f'{k} {v}' for k, v in sorted(kinds.items()))}) -> audio/sfx.wav")


def main_sfx(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    a = ap.parse_args(argv)
    build_sfx(pathlib.Path(a.project).resolve())


def main_mix(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--music", default=None, help="a music file you have the rights to")
    ap.add_argument("--music-gain", type=float, default=-20.0)
    ap.add_argument("--sfx-gain", type=float, default=-8.0)
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    ad = proj / "audio"
    if not (ad / "sfx.wav").exists():
        build_sfx(proj)
    dur = json.loads((ad / "timing.json").read_text(encoding="utf-8"))["total_duration"]
    inputs = ["-i", ad / "narration.m4a", "-i", ad / "sfx.wav"]
    graph = f"[1:a]volume={a.sfx_gain}dB[fx];"
    mixed = "[0:a][fx]"
    n = 2
    if a.music:
        inputs += ["-stream_loop", "-1", "-i", pathlib.Path(a.music).resolve()]
        graph += (f"[2:a]volume={a.music_gain}dB,afade=t=out:st={max(0, dur - 3):.2f}:d=3[mu];"
                  f"[mu][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck];")
        mixed += "[duck]"
        n = 3
    graph += f"{mixed}amix=inputs={n}:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[out]"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]", "-t", f"{dur:.3f}",
         "-ar", str(R), "-c:a", "aac", "-b:a", "192k", ad / "mix.m4a"], "Mixing the soundtrack failed")
    print("mix: audio/mix.m4a (-14 LUFS)" + (" with music ducked under the voice" if a.music else ""))


main = main_sfx

"""Cut one recording of the whole script into one clip per line.

  docuframe split --project P [--script script.split.json]

Reads audio/takes/<take>.wav for every take in the script. Pauses in the recording are candidate
cut points; the expected position of each line boundary comes from how much text precedes it. A
small dynamic program picks, in order, the pause nearest each expected boundary (long pauses win
ties), so one misplaced cut cannot shift all the lines after it.

If a cut lands wrong, force it: audio/overrides.json {"cut_before": {"7": 41.2}} (line id: seconds
into its take). Writes audio/lines/segNN.wav, audio/segments.json and audio/lines/split_report.json;
lines whose speaking rate is far from the median are listed — listen to those.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

import numpy as np

from . import audio as A


def weight(text):
    """How long a line takes to say, in rough letter units (pauses at punctuation count too)."""
    return sum(ch.isalnum() for ch in text) + 5 * len(re.findall(r"[,،、，;:]", text)) + 10 * len(re.findall(r"[.!?。！？؟]", text))


def pauses(x, min_len=0.16):
    """[(start s, end s)] of quiet stretches inside the speech."""
    env = A.envelope(x)
    if len(env) < 3:
        return []
    speech = np.percentile(env, 90)
    quiet = env < max(speech - 28, -50)
    out, k = [], 0
    while k < len(quiet):
        if quiet[k]:
            j = k
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - k) * 0.02 >= min_len:
                out.append((k * 0.02, j * 0.02))
            k = j
        else:
            k += 1
    return out


def choose_cuts(cands, expected):
    """Pick len(expected) cut points from candidate pauses, in order, closest to the expected times."""
    n, m = len(expected), len(cands)
    if n == 0:
        return []
    if m < n:
        return list(expected)
    INF = 1e18
    best = np.full((n + 1, m + 1), INF)
    back = np.zeros((n + 1, m + 1), int)
    best[0, :] = 0
    mids = [(s + e) / 2 for s, e in cands]
    lens = [e - s for s, e in cands]
    for i in range(1, n + 1):
        run_min, arg = INF, -1
        for j in range(1, m + 1):
            if best[i - 1, j - 1] < run_min:
                run_min, arg = best[i - 1, j - 1], j - 1
            cost = abs(mids[j - 1] - expected[i - 1]) - 0.6 * min(lens[j - 1], 1.0)
            best[i, j] = run_min + cost
            back[i, j] = arg
    j = int(np.argmin(best[n, 1:])) + 1
    picks = []
    for i in range(n, 0, -1):
        picks.append(mids[j - 1])
        j = back[i, j]
    return picks[::-1]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--script", default="script.json")
    ap.add_argument("--gap", type=float, default=0.4)
    ap.add_argument("--take-gap", type=float, default=0.9)
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    script = json.loads((proj / a.script).read_text(encoding="utf-8"))
    ov = proj / "audio" / "overrides.json"
    forced = {str(k): float(v) for k, v in (json.loads(ov.read_text(encoding="utf-8")).get("cut_before", {}) if ov.exists() else {}).items()}
    out = proj / "audio" / "lines"
    out.mkdir(parents=True, exist_ok=True)
    segments, report = [], []
    for take in script["takes"]:
        wav = proj / "audio" / "takes" / f"{take['take']}.wav"
        if not wav.exists():
            raise SystemExit(f"Missing recording {wav}.")
        x = A.read(wav)
        i0, i1 = A.speech_bounds(x)
        t0, t1 = i0 / A.RATE, i1 / A.RATE
        lines = take["lines"]
        w = [weight(ln["spoken"]) for ln in lines]
        total = sum(w) or 1
        acc, expected = 0, []
        for k in range(len(lines) - 1):
            acc += w[k]
            expected.append(t0 + (t1 - t0) * acc / total)
        cands = [(s, e) for s, e in pauses(x[i0:i1]) if True]
        cands = [(s + t0, e + t0) for s, e in cands]
        cuts = choose_cuts(cands, expected)
        for k in range(1, len(lines)):
            if str(lines[k]["id"]) in forced:
                cuts[k - 1] = forced[str(lines[k]["id"])]
        edges = [t0] + cuts + [t1]
        for k, ln in enumerate(lines):
            s, e = edges[k], edges[k + 1]
            clip = x[int(s * A.RATE):int(e * A.RATE)]
            A.write(out / f"seg{ln['id']:02d}.wav", clip)
            last = k == len(lines) - 1
            segments.append({"id": ln["id"], "scene": take["take"], "caption": ln["text"], "vo": ln["spoken"],
                             "gap_after": ln.get("gap_after", a.take_gap if last else a.gap)})
            report.append({"id": ln["id"], "take": take["take"], "start": round(s, 3), "end": round(e, 3),
                           "rate": round(weight(ln["spoken"]) / max(0.1, e - s), 2)})
    rates = [r["rate"] for r in report]
    med = float(np.median(rates)) if rates else 0
    odd = [r["id"] for r in report if med and abs(r["rate"] - med) / med > 0.35]
    (proj / "audio" / "segments.json").write_text(json.dumps({"segments": segments}, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "split_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"split: {len(segments)} lines" + (f"; check lines {odd} (speaking rate looks off — a cut may be misplaced)" if odd else ""))

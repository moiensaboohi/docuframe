"""Word-level timing: when each spoken word starts, so hits land on the word (target: within 80 ms).

  docuframe align --project P            # needs: pip install faster-whisper (MIT)
  docuframe align --project P --model small

Each narration line is cut from audio/narration.m4a and transcribed with word timestamps; the
recognised words are matched to the script's spoken words in order (so recognition errors don't
shift anything: unmatched words are interpolated between matched neighbours). The result is stored
as "words" on each segment of audio/timing.json, which the scene builder and captions use.

Without this step, word times are estimated from each word's share of the line's letters. That is
usually within 150-250 ms; docuframe check reports which method was used.
"""
from __future__ import annotations

import argparse
import difflib
import json
import pathlib
import tempfile

from .util import run


def norm(w):
    return "".join(ch for ch in w.lower() if ch.isalnum())


def match(spoken_words, rec):
    """Map recognised (word, start, end) onto the script's spoken words; interpolate the rest."""
    a = [norm(w) for w in spoken_words]
    b = [norm(r[0]) for r in rec]
    times = [None] * len(a)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = (rec[blk.b + k][1], rec[blk.b + k][2])
    matched = sum(t is not None for t in times)
    # interpolate gaps by letter share between known anchors
    known = [i for i, t in enumerate(times) if t]
    if not known:
        return None, 0.0
    for i in range(len(times)):
        if times[i] is None:
            lo = max([k for k in known if k < i], default=None)
            hi = min([k for k in known if k > i], default=None)
            t_lo = times[lo][1] if lo is not None else rec[0][1]
            t_hi = times[hi][0] if hi is not None else rec[-1][2]
            span = [len(a[j]) or 1 for j in range((lo + 1) if lo is not None else 0, hi if hi is not None else len(a))]
            pos = i - ((lo + 1) if lo is not None else 0)
            acc = sum(span[:pos]); tot = sum(span) or 1
            st = t_lo + (t_hi - t_lo) * acc / tot
            times[i] = (st, st + (t_hi - t_lo) * span[pos] / tot)
    return times, matched / max(1, len(a))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--model", default="base")
    ap.add_argument("--lang", default=None)
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("Word alignment is optional and not installed. Run:  pip install faster-whisper\n"
                         "(Without it, word times are estimated from letter counts.)")
    tp = proj / "audio" / "timing.json"
    timing = json.loads(tp.read_text(encoding="utf-8"))
    voice = proj / "audio" / "voice.json"
    lang = a.lang or (json.loads(voice.read_text(encoding="utf-8")).get("lang") if voice.exists() else None) or "en"
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    narr = proj / "audio" / "narration.m4a"
    report = []
    with tempfile.TemporaryDirectory() as td:
        for seg in timing["segments"]:
            wav = pathlib.Path(td) / f"s{seg['id']}.wav"
            pad = 0.25
            t0 = max(0.0, seg["start"] - pad)
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{seg['end'] - t0 + pad:.3f}", "-i", narr,
                 "-ar", "16000", "-ac", "1", wav], "Cutting a line for alignment failed")
            segs, _ = model.transcribe(str(wav), language=lang.split("-")[0], word_timestamps=True, vad_filter=False,
                                       initial_prompt=seg["vo"])
            rec = [(w.word.strip(), t0 + w.start, t0 + w.end) for s in segs for w in (s.words or [])]
            from .captions import _tokens
            spoken = _tokens(seg["vo"])
            times, score = match(spoken, rec) if rec else (None, 0.0)
            if times:
                seg["words"] = [{"w": w, "start": round(s, 3), "end": round(e, 3)} for w, (s, e) in zip(spoken, times)]
            report.append({"id": seg["id"], "matched": round(score, 2)})
            print(f"  line {seg['id']:>3}: {score * 100:3.0f}% of words matched", flush=True)
    timing["alignment"] = {"method": "faster-whisper", "model": a.model, "lang": lang}
    tp.write_text(json.dumps(timing, indent=2, ensure_ascii=False), encoding="utf-8")
    low = [r for r in report if r["matched"] < 0.6]
    print(f"aligned {len(report)} lines" + (f"; low match on lines {[r['id'] for r in low]}: listen to them" if low else ""))

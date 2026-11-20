"""Narration: a local voice per line, or the user's own recording.

  docuframe voice --project P                      # local Kokoro voice (downloads ~120 MB once)
  docuframe voice --project P --voice bf_emma      # another voice (docuframe voice --list)
  docuframe voice --project P --engine system      # the OS voice: macOS say, Windows SAPI, Linux espeak-ng
  docuframe voice --project P --audio my_read.wav  # your own recording of the whole script

Every line is synthesised on its own, so line timing is exact and no silence detection is needed.
With --audio, the recording is split into lines by its pauses (docuframe split does the work).
Writes audio/lines/segNN.wav and audio/segments.json; then run docuframe narration.

Languages the local voice speaks: English (US/UK), Spanish, French, Hindi, Italian, Brazilian
Portuguese, Japanese, Mandarin Chinese. For Arabic, Persian, Urdu, Hebrew, Bengali, Tamil and
others, use your own recording, --engine system (robotic but free), or --engine cmd with any TTS.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

from .fonts import _download, cache_dir

MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODEL, VOICES = "kokoro-v1.0.int8.onnx", "voices-v1.0.bin"

# language code -> (Kokoro lang, default voice)
KOKORO_LANGS = {
    "en": ("en-us", "am_michael"), "en-us": ("en-us", "am_michael"), "en-gb": ("en-gb", "bm_george"),
    "es": ("es", "em_alex"), "fr": ("fr-fr", "ff_siwis"), "hi": ("hi", "hm_omega"), "it": ("it", "im_nicola"),
    "pt": ("pt-br", "pm_alex"), "pt-br": ("pt-br", "pm_alex"), "ja": ("ja", "jm_kumo"), "zh": ("cmn", "zm_yunjian"),
}
# Experimental: the local voice reads these through espeak-ng phonemes with an English speaker, so it
# sounds accented. Good for drafts and timing; publish with your own recording or a native TTS.
KOKORO_EXPERIMENTAL = {"ar": ("ar", "am_michael"), "fa": ("fa", "am_michael"), "ur": ("ur", "am_michael"),
                       "he": ("he", "am_michael"), "bn": ("bn", "hm_omega"), "ta": ("ta", "hm_omega"), "de": ("de", "am_michael")}
ESPEAK_LANG = {"ar": "ar", "fa": "fa", "ur": "ur", "he": "he", "bn": "bn", "ta": "ta", "tr": "tr", "de": "de", "ru": "ru"}


def load_script(proj: pathlib.Path) -> dict:
    p = proj / "script.json"
    if not p.exists():
        raise SystemExit(f"{p} not found. Write the script first (docuframe new makes a template).")
    s = json.loads(p.read_text(encoding="utf-8"))
    if "takes" not in s:      # flat form: {"lines": [...]} -> one take per chapter (or one take)
        takes, cur = [], None
        for ln in s.get("lines", []):
            ch = ln.get("chapter") or (cur["take"] if cur else "T01")
            if cur is None or ch != cur["take"]:
                cur = {"take": ch, "lines": []}; takes.append(cur)
            cur["lines"].append(ln)
        s["takes"] = takes
    for t in s["takes"]:
        for ln in t["lines"]:
            ln.setdefault("spoken", ln["text"])
    return s


def lines_of(script: dict) -> list[tuple[str, dict]]:
    return [(t["take"], ln) for t in script["takes"] for ln in t["lines"]]


def model_paths(fetch=True):
    d = cache_dir().parent / "voice"
    d.mkdir(parents=True, exist_ok=True)
    m, v = d / MODEL, d / VOICES
    for p in (m, v):
        if not p.exists():
            if not fetch:
                return None
            print(f"downloading {p.name} (once) ...", flush=True)
            _download(MODEL_URL + p.name, p)
    return m, v


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise SystemExit(f"This step failed: {' '.join(map(str, cmd))}\n{r.stderr[-1500:]}")
    return r.stdout


def to_wav(src, dst):
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ar", "48000", "-ac", "1", str(dst)])


def synth_kokoro(lines, lang, voice, speed, outdir):
    try:
        import soundfile as sf
        from kokoro_onnx import Kokoro
    except ImportError:
        raise SystemExit("The local voice is not installed. Run:  pip install kokoro-onnx soundfile  (or: docuframe doctor --fix)")
    base = lang.split("-")[0].lower()
    klang, kvoice = KOKORO_LANGS.get(lang.lower(), KOKORO_LANGS.get(base, (None, None)))
    experimental = False
    if klang is None and base in KOKORO_EXPERIMENTAL:
        klang, kvoice = KOKORO_EXPERIMENTAL[base]
        experimental = True
        print(f"note: the local voice reads {lang!r} with an accent (draft quality). For publishing, record it yourself "
              f"(docuframe voice --audio file.wav) or use a native voice (--engine cmd).", flush=True)
    if klang is None:
        raise SystemExit(f"The local voice does not speak {lang!r}. Use --audio with your own recording, "
                         f"--engine system, or --engine cmd with another TTS.")
    m, v = model_paths()
    k = Kokoro(str(m), str(v))
    voice = voice or kvoice
    if voice not in k.get_voices():
        raise SystemExit(f"voice {voice!r} not found. Voices: {', '.join(sorted(k.get_voices()))}")
    t0 = time.time()
    for i, (take, ln) in enumerate(lines):
        samples, sr = k.create(ln["spoken"], voice=voice, speed=speed, lang=klang)
        tmp = outdir / f"_k{ln['id']:02d}.wav"
        sf.write(str(tmp), samples, sr)
        to_wav(tmp, outdir / f"seg{ln['id']:02d}.wav"); tmp.unlink()
        el = time.time() - t0
        eta = el / (i + 1) * (len(lines) - i - 1)
        print(f"  line {ln['id']:>3} ({i + 1}/{len(lines)})  eta {eta:4.0f}s", flush=True)
    return {"engine": "kokoro-onnx", "model": MODEL, "voice": voice, "lang": klang, "licence": "Apache-2.0 (model weights)",
            "synthetic": True, "experimental_language": experimental}


def synth_system(lines, lang, voice, outdir):
    with tempfile.TemporaryDirectory() as td:
        for take, ln in lines:
            txt = pathlib.Path(td) / "l.txt"; txt.write_text(ln["spoken"], encoding="utf-8")
            raw = pathlib.Path(td) / "l.wav"
            if sys.platform == "darwin":
                aiff = pathlib.Path(td) / "l.aiff"
                run(["say", "-f", str(txt), "-o", str(aiff)] + (["-v", voice] if voice else [])); to_wav(aiff, raw)
            elif sys.platform == "win32":
                ps = ("Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                      + (f"$s.SelectVoice('{voice}'); " if voice else "")
                      + f"$s.SetOutputToWaveFile('{raw}'); $s.Speak([IO.File]::ReadAllText('{txt}')); $s.Dispose()")
                run(["powershell", "-NoProfile", "-Command", ps])
            else:
                exe = shutil.which("espeak-ng") or shutil.which("espeak")
                if not exe:
                    raise SystemExit("No system voice found. Install espeak-ng (docuframe doctor shows how), or use --audio.")
                run([exe, "-v", voice or ESPEAK_LANG.get(lang.split("-")[0], "en"), "-f", str(txt), "-w", str(raw)])
            to_wav(raw, outdir / f"seg{ln['id']:02d}.wav")
            print(f"  line {ln['id']}", flush=True)
    return {"engine": "system", "voice": voice or "default", "synthetic": True}


def synth_cmd(lines, cmd, outdir):
    with tempfile.TemporaryDirectory() as td:
        for take, ln in lines:
            txt = pathlib.Path(td) / "l.txt"; txt.write_text(ln["spoken"], encoding="utf-8")
            raw = pathlib.Path(td) / "l.wav"
            subprocess.run(cmd.format(txt=txt, out=raw), shell=True, check=True)
            to_wav(raw, outdir / f"seg{ln['id']:02d}.wav")
    return {"engine": "cmd", "cmd": cmd, "synthetic": True}


def write_segments(proj, script, gap, take_gap):
    segs = []
    lines = lines_of(script)
    for i, (take, ln) in enumerate(lines):
        last = i == len(lines) - 1 or lines[i + 1][0] != take
        segs.append({"id": ln["id"], "scene": take, "caption": ln["text"], "vo": ln["spoken"],
                     "gap_after": ln.get("gap_after", take_gap if last else gap)})
    (proj / "audio" / "segments.json").write_text(json.dumps({"segments": segs}, indent=1, ensure_ascii=False), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--engine", default="kokoro", choices=["kokoro", "system", "cmd"])
    ap.add_argument("--voice", default=None)
    ap.add_argument("--lang", default=None, help="defaults to script.json lang, else en")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--cmd", default=None, help="any TTS command with {txt} and {out}")
    ap.add_argument("--audio", default=None, help="your own recording of the whole script")
    ap.add_argument("--gap", type=float, default=0.35)
    ap.add_argument("--take-gap", type=float, default=0.8)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    proj = pathlib.Path(a.project).resolve()
    if a.list:
        from kokoro_onnx import Kokoro
        m, v = model_paths()
        print("\n".join(sorted(Kokoro(str(m), str(v)).get_voices())))
        return
    script = load_script(proj)
    lang = a.lang or script.get("lang", "en")
    adir = proj / "audio"; ldir = adir / "lines"; ldir.mkdir(parents=True, exist_ok=True)
    if a.audio:
        # own recording: one take containing every line, split by pauses
        tdir = adir / "takes"; tdir.mkdir(parents=True, exist_ok=True)
        merged = {"title": script.get("title", ""), "takes": [{"take": "ALL", "lines": [ln for _, ln in lines_of(script)]}]}
        (proj / "script.split.json").write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
        to_wav(pathlib.Path(a.audio).resolve(), tdir / "ALL.wav")
        from . import voice_split
        voice_split.main(["--project", str(proj), "--script", "script.split.json"])
        info = {"engine": "user-audio", "file": str(a.audio), "synthetic": False}
    else:
        lines = lines_of(script)
        print(f"voicing {len(lines)} lines ({a.engine}, {lang})", flush=True)
        if a.engine == "kokoro":
            info = synth_kokoro(lines, lang, a.voice, a.speed, ldir)
        elif a.engine == "system":
            info = synth_system(lines, lang, a.voice, ldir)
        else:
            if not a.cmd:
                raise SystemExit("--engine cmd needs --cmd 'tts --in {txt} --out {out}'")
            info = synth_cmd(lines, a.cmd, ldir)
        write_segments(proj, script, a.gap, a.take_gap)
    info["lang"] = lang
    (adir / "voice.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print("voice done -> audio/lines, audio/segments.json. Next: docuframe narration --project", proj.name)


if __name__ == "__main__":
    main()

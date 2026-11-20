# Method decisions (draft for owner approval)

Date: 2026-11-20. Status: **proposed** — re-check after the first end-to-end test and again after evals.

## 1. Rendering engine

Spike evidence (this machine, 2 vCPU, no GPU):
- **Python + skia-python 144.1:** 300 frames of 1080p with 40 shapes + text, piped to ffmpeg (x264 veryfast) in 6.1 s = **49 fps, peak RSS 74 MB**.
- **Text shaping:** Persian (Vazirmatn), Arabic (Noto Sans Arabic) and Hindi (Noto Sans Devanagari) rendered correctly with `skia.textlayout` + ICU — joined letters, correct bidi with embedded Latin and digits, correct Devanagari conjuncts. Base direction needs Unicode isolates (U+2067…U+2069) because the Python binding doesn't expose paragraph direction. Image: `research/media/spike-rtl-indic-shaping.png`.

| Criterion | A. React frames (Remotion) | B. HTML + headless Chrome capture (own runtime or HyperFrames) | C. Python + Skia (own engine) | D. Hybrid: C default + B for optional "web scene" |
|---|---|---|---|---|
| Output quality | high | highest (CSS, SVG, filters, any web font) | high (2D vector, images, blur, shaders via SkSL) | high |
| Determinism | good (frame-addressed) | good if time is virtualised; worker-order bugs exist upstream | **exact** (pure function of t) | exact for C scenes |
| Editability by users/agents | React code | **HTML (agents write it best)** | Python + **scene JSON** | scene JSON for both |
| Install weight | Node + Chromium + ~16 pkgs | Node + Chromium (~150–300 MB) | **pip wheel ~60 MB + ffmpeg** | C + Chromium only if used |
| First-run time | slow | medium | **fast** | fast |
| Render speed | medium | slow (screenshot per frame) | **fast (49 fps measured)** | fast |
| Memory | high (Chrome per worker) | high | **very low** | low |
| Cost per run | free ≤3 staff, else paid | free | free | free |
| Offline | yes | yes | yes | yes |
| Windows / macOS / Linux | ok | known Windows bugs (console windows, server, WSL GPU) | **prebuilt wheels all three** | ok |
| Runs inside Claude app sandbox (no terminal) | unlikely | uncertain (needs Chromium) | **likely (pip + ffmpeg)** | C path yes |
| RTL / Indic | browser-grade | browser-grade (but upstream per-letter split bug) | **verified in spike** | yes |
| Licence / business terms | ❌ company licence | ✅ Apache/own | ✅ BSD-3 | ✅ |

**Proposed decision: D — Python + Skia engine as the default and only required renderer; scenes and styles are data (JSON); an optional HTML capture path later, only for users who want CSS-built scenes.** Reasons: lightest install (the #1 complaint), fastest and memory-safe for 30-minute films on 16 GB, works on Windows from wheels, most likely to run inside the Claude app without a terminal, fully free licence, and RTL/Indic shaping already verified.

Trade-off accepted: agents write Skia code less fluently than HTML. Mitigation: agents rarely write drawing code — they write **scene JSON** against a scene library we build and test once; drawing code lives in `core/`.

## 2. Camera model
Support both, as style properties:
- **World board:** one continuous camera over a laid-out world (evidence board, vintage atlas, case file).
- **Scene cuts:** scene-by-scene with designed transitions (flat explainer, newsroom, lab notebook).
Same scene library; the layout pass decides whether scenes are placed on one world canvas or in sequence.

## 3. Voice
- **Default:** user's own audio, or local Kokoro (Apache-2.0) via onnxruntime — no torch.
- **Optional:** cloud TTS with the user's key (any provider), off by default.
- **Not bundled:** Piper (GPL-3.0).
- **Open:** espeak-ng (GPL-3.0) is needed for Kokoro's non-English phonemes — see owner question.

## 4. Timing
- faster-whisper (MIT) word timestamps on our own TTS output or user audio; for TTS we already know the text, so we align known text to audio and check drift ≤ 80 ms per anchored word.
- WhisperX alignment models only after per-language licence check.

## 5. Delivery format
- Skill folder (SKILL.md + references + scripts + styles), `core/` Python package installed from the repo (no remote bootstrap script), `doctor` in Python with a PowerShell + sh launcher.

## 6. To re-check after first end-to-end test
- Real-scene fps with photos, blur, grain at 1080p (target ≥15 fps on 4 cores).
- Whether skia-python + ffmpeg are importable in the Claude app sandbox.
- Hebrew, Urdu Nastaliq, Bengali, Tamil, Chinese, Japanese shaping.

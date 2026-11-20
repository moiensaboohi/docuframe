# Licences — verified 2026-11-20

Each entry was checked from the LICENSE file or package metadata on this date (npm registry `license` field, PyPI wheel METADATA, or the project's own licence page). Re-check before every release; licences change.

Legend: ✅ may use (as dependency or vendored with notice) · ⚠️ use with conditions / ask owner · ❌ study only, never reuse code or assets.

## Rendering and graphics

| Item | Version checked | Licence (source) | Verdict | Notes |
|---|---|---|---|---|
| skia-python | 144.1 | BSD-3 (PyPI classifier + LICENSE) | ✅ | Python 2D engine with HarfBuzz-based text shaping via `skia.textlayout` (Paragraph) — needed for RTL/Indic. |
| skia-canvas (npm) | 4.0.1 | MIT (npm) | ✅ | Node alternative to skia-python. |
| @napi-rs/canvas | 1.1.1 | MIT (npm) | ✅ | Node Skia canvas, prebuilt binaries incl. Windows. |
| harfbuzzjs | 1.6.4 | MIT (npm) | ✅ | Shaping if we go the JS route. |
| Playwright | 1.65.1 | Apache-2.0 (npm) | ✅ | Headless Chrome capture. Downloads Chromium (~150 MB+). |
| Puppeteer | 25.18.1 | Apache-2.0 (npm) | ✅ | Same role. |
| HyperFrames | 0.9.70 | Apache-2.0 (npm) | ✅ | HTML+GSAP video framework. Engine bugs on Windows/RTL (see landscape). |
| mediabunny | 1.66.2 | MPL-2.0 (npm) | ⚠️ | File-level copyleft: fine as an unmodified dependency; modified files must stay MPL. |
| **Remotion** | 4.0.545 | Custom "Remotion License" (LICENSE.md) | ⚠️ | Free for individuals, for-profit orgs with **up to 3 employees**, non-profits, evaluation. Otherwise a Company Licence: "Creators" $25/seat/month, "Automators" $0.01/render with $100/month minimum, Enterprise from $500/month (remotion.dev/license, read 2026-11-20). LICENSE.md says the licence will "slightly change" in Remotion 5.0. **Cannot be our default** (rule 1.1.7); could be an optional engine with the terms stated in README. |
| GSAP | 3.15.1 | "Standard no-charge licence" (gsap.com/standard-license) | ⚠️ | Commercial use free **unless end users pay a fee to use the product**; no redistribution of source to third parties without consent. Our skill is free, but a user who builds a paid SaaS on our output pipeline would need a GSAP Business licence. Avoid as a core dependency; write our own easing/tween code. |
| FFmpeg | system | LGPL-2.1+ / GPL depending on build | ⚠️ | Call it as an external program, never bundle a GPL build in our zip. Devcontainer installs distro ffmpeg (user's own install). Record in README. |

## Voice (TTS) and alignment

| Item | Version | Licence | Verdict | Notes |
|---|---|---|---|---|
| Kokoro (Python) | 0.7.16 | Apache-2.0 (PyPI) | ✅ | Model weights (Kokoro-82M) Apache-2.0. Depends on torch (~large) and misaki. |
| kokoro-onnx | 0.6.1 | MIT (LICENSE in wheel) | ✅ | Lighter (onnxruntime, no torch). **Depends on `phonemizer` + `espeakng-loader` → espeak-ng (GPL-3.0).** |
| misaki (G2P) | 0.7.4 | Apache-2.0 | ✅ | English G2P without espeak; other languages fall back to espeak-ng. |
| phonemizer-fork | 3.3.2 | **GPL-3.0+** | ⚠️ | Pulled in by Kokoro for non-English. |
| kokoro-js (npm) | 1.2.1 | Apache-2.0 | ⚠️ | Depends on npm `phonemizer` (Apache-2.0 wrapper) which ships **espeak-ng compiled to WASM (GPL-3.0)**. |
| **piper-tts** | 1.8.0 | **GPL-3.0-or-later** (PyPI) | ❌ as dependency we ship | The project moved to GPL. Can be an optional user-installed engine, never bundled. |
| faster-whisper | 1.2.1 | MIT | ✅ | Transcription with word timestamps; CTranslate2 (MIT). Whisper weights MIT. |
| WhisperX | 3.8.6 | BSD-2-Clause | ✅ | Forced alignment uses per-language wav2vec2 models from Hugging Face — **each model has its own licence; check per language** before enabling. |

**Open licence question for the owner (espeak-ng):** every free multilingual local TTS path we found uses espeak-ng (GPL-3.0) for phonemes outside English. Calling a separately installed GPL program/library does not change our MIT licence in common practice, but bundling it in our release zip or devcontainer image would make that bundle a GPL distribution. Options: (a) English-only bundled voice; other languages install espeak-ng on first use as the user's own dependency; (b) treat espeak-ng as a system dependency like ffmpeg; (c) user's own audio / optional cloud TTS for non-English. **Needs your decision.**

## Fonts

| Item | Licence | Verdict | Notes |
|---|---|---|---|
| Noto Sans / Serif families incl. Arabic, Hebrew, Devanagari, Bengali, Tamil, CJK | SIL OFL 1.1 | ✅ | Full script coverage. CJK files are large (~15–20 MB each) → fetch on demand, don't bundle. |
| Vazirmatn (Persian) | SIL OFL 1.1 | ✅ (verify at fetch) | Good Persian/Arabic UI face. |
| Noto Nastaliq Urdu | SIL OFL 1.1 | ✅ | Needed for Urdu. |
| Other display faces | per family | verify each | Only OFL/Apache/CC0 from Google Fonts metadata; record each in `THIRD_PARTY_NOTICES.md`. |

## Media sources (for user films; checked per item at fetch time)

| Source | Status | What the skill must do |
|---|---|---|
| Wikimedia Commons | Per-file licence (PD, CC0, CC-BY, CC-BY-SA, …) | Read `extmetadata` (LicenseShortName, Artist, Credit, UsageTerms) per file. Allow PD/CC0/CC-BY by default; CC-BY-SA allowed only with a warning that the derivative image must stay CC-BY-SA (fine for a film frame with attribution, but say so); reject NC/ND. Auto-write attribution. |
| Library of Congress | "Free to use" sets are described as rights-free, but rights are stated item by item ("unless otherwise noted") | Read the item's rights field; never assume. |
| NASA | Generally not copyrighted; **logos/insignia restricted, no implied endorsement, identifiable astronauts need permission for commercial use, third-party-credited images not covered**; NASA should be credited as source (nasa.gov brand center, read 2026-11-20) | Block NASA insignia in promo/thumbnail use; add "Source: NASA"; flag images credited to third parties. |
| Europeana | `edm:rights` URI per item (rightsstatements.org / CC) | Accept only PD-mark, CC0, CC-BY, (CC-BY-SA with warning). |
| National archives (US NARA etc.) | Mostly PD for federal works, with exceptions | Read item rights field. |
| Natural Earth (map data) | Public domain | ✅ for map scenes. |
| OpenStreetMap | ODbL | ⚠️ Rendered map images need "© OpenStreetMap contributors"; auto-add. |

## Projects studied for ideas only (licence forbids reuse)

| Repo | Licence | Why ❌ |
|---|---|---|
| anything2explainer, video-talkcraft, onetake | PolyForm Noncommercial 1.0.0 | Noncommercial |
| lemo-opuscar docs | CC-BY-NC-4.0 (code is MIT) | Noncommercial docs; we don't take its code either |
| OpenMontage, frametell | AGPL-3.0 | Copyleft would force our licence |

MIT/Apache repos (cinecode, cinematic-skill, explainroo, huashu-art-motion, BB-Video, videowright, motlab, vox-director, …) are **legally reusable with notice**, but rule 1.1.1 says write our own; we reuse nothing from them unless a specific item is justified and logged in `THIRD_PARTY_NOTICES.md`.

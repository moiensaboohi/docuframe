# Third-party notices

This is the only file in this repository that names other projects. docuframe's own code is MIT
(see LICENSE) and was written for this project; `tools/provenance_check.py` measures its overlap
with any other codebase. Nothing below is copied into this repository: everything is a dependency
installed on the user's machine or a file fetched on first use. Licences verified 2026-11-20
(details: research/licences.md).

## Python dependencies (installed by pip)

| Project | Licence | Used for |
|---|---|---|
| skia-python (Skia) | BSD-3-Clause | drawing every frame, text shaping (HarfBuzz, ICU) |
| NumPy | BSD-3-Clause | image arrays |
| Pillow | MIT-CMU (HPND) | image loading and grading |
| fontTools | MIT | static instances of variable fonts |
| kokoro-onnx (optional) | MIT | local voice runtime |
| Kokoro-82M model weights (optional, downloaded) | Apache-2.0 | local voice |
| misaki (optional, via kokoro) | Apache-2.0 | English phonemes |
| phonemizer / espeak-ng (optional, via kokoro-onnx) | GPL-3.0 | phonemes for non-English voice; installed separately by pip, not distributed by docuframe |
| onnxruntime (optional) | MIT | voice inference |
| faster-whisper (optional) | MIT | word timing |
| SciPy (optional) | BSD-3-Clause | faster sound-effect synthesis |

## External programs

| Program | Licence | Used for |
|---|---|---|
| FFmpeg | LGPL-2.1+ / GPL (depends on the build the user installs) | encoding, audio; called as a separate program, never bundled |

## Fonts (fetched on first use, saved with their licence text)

All SIL Open Font License 1.1: Oswald, Libre Baskerville, Courier Prime, Homemade Apple (Apache-2.0),
Montserrat, Inter, Space Mono, Playfair Display, Special Elite (Apache-2.0), Noto Sans, Noto Sans
Arabic, Hebrew, Devanagari, Bengali, Tamil, Thai, SC, JP, KR, Noto Nastaliq Urdu, Vazirmatn,
Archivo Black, DM Serif Display, Caveat, Space Grotesk, Poppins, DM Sans, Anton, IBM Plex Mono,
Fraunces, Syne, Bricolage Grotesque, Instrument Serif, Geist, Inter Tight, Roboto, Figtree, Instrument Sans,
Manrope, Plus Jakarta Sans, Newsreader. Variable fonts are cut to static weights
locally with fontTools; the OFL allows this, and the cut files keep the original names and licence.

## Data sources the skill can fetch for a user's film

| Source | Terms | Attribution |
|---|---|---|
| Wikimedia Commons | per file (public domain, CC0, CC BY, CC BY-SA accepted; NC/ND refused) | written into the description and manifest automatically |
| Natural Earth (maps) | public domain | none required; credited |
| OpenStreetMap (if used) | ODbL | "© OpenStreetMap contributors" added automatically |


# Eval results

| date | what ran | result | changes made |
|---|---|---|---|
| 2026-11-20 | 3 fixtures (English 16:9 photos, Persian RTL 16:9, Hindi 9:16) on Linux, local voice, stills + check + full render of two | check 0 fail on all three after fixes | fixed: title overflow, decimal numbers, camera sliding through clusters, beats too short to read, variable fonts rendering thin, quote layout, vertical comparison layout, source labels in the film's language, overlays under the vignette |

| 2026-11-20 | Provenance: `tools/provenance_check.py` (identifier- and literal-normalised token runs) against the third-party repo studied in research | highest file 23.0 % at 15-token runs; an unrelated codebase scores up to 26.7 % on the same files (shared Python/Skia idioms) | engine, assets, captions, burn, archive, narration, line splitting, sound and maps rewritten from scratch with a new item model, caption method and grading |

Not yet run: the 19 prompts end to end with a fresh agent, Windows/macOS first-run timing (runs in CI
once the repo can push), the blind non-technical tester, the comparison benchmark against other skills.

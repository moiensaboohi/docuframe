# Synthesis — what docuframe must be

Date: 2026-11-20. Built from `landscape.md`, `licences.md`, `platform-policies.md` and craft research. Feature-matrix cells come from reading each repo's SKILL.md/README and a keyword pass over its files; "partial" means present but limited or undocumented. Re-verify cells before quoting them publicly (the README benchmark will use run results, not this table).

## 1. Feature matrix

Columns: AE = topic→explainer NC skill · TC = voiceover explainer NC skill · CC = films-in-code MIT skill · CS = evidence-board MIT skill · ER = local-voice explainer CLI · OM = AGPL general studio · Paid = typical faceless-video SaaS · **DF = docuframe (target)**

| Capability | AE | TC | CC | CS | ER | OM | Paid | **DF** |
|---|---|---|---|---|---|---|---|---|
| Topic → researched script with sources | partial | no | no | partial | partial | yes | yes (unsourced) | **yes, per-claim** |
| Fact sheet; unsourced claims flagged before voice | no | no | no | no | no | partial | no | **yes** |
| Finished script / own audio input | yes | yes | yes | yes | yes | yes | yes | **yes** |
| Local TTS, no key | no | optional | no | partial | **yes** | partial | no | **yes** |
| Word-level timing | partial | **yes** | partial | yes | yes | yes | partial | **yes, ±80 ms check** |
| Deterministic code-drawn visuals | yes | yes | yes | yes | yes | partial | no | **yes** |
| Approval checkpoint before heavy render | **yes** | yes | yes | partial | partial | partial (unenforced) | no | **yes, enforced** |
| Self-review of rendered frames | yes | **yes** | partial | **yes** | yes | partial | no | **yes, ≤5 rounds, report** |
| Styles | 1 | 1 | many | 2 | ~4 looks | many | templates | **10+ as data packs** |
| Map scenes (borders by year, routes) | no | no | no | partial | no | partial | no | **yes** |
| Chart / big number / timeline scenes | yes | yes | partial | yes | yes | yes | partial | **yes** |
| Archive photo + per-item licence line | no | no | no | **yes** | no | partial | stock | **yes, automatic** |
| 9:16 / 1:1 from same project | partial | yes | partial | no | yes | yes | yes | **yes, auto-cut** |
| Long-form (20–30 min) on 16 GB, resumable | no | no | no | partial | no | requested | cloud | **yes, measured** |
| Captions SRT/VTT | burned | yes | yes | yes | yes | yes | yes | **yes, word-exact check** |
| YouTube package (titles, description, sources, chapters, thumbnails) | no | no | partial | no | partial | partial | partial | **yes** |
| Dubbing / re-timed other languages | no | no | no | voice re-time | partial | partial | yes (paid) | **yes** |
| RTL (Arabic, Persian, Urdu, Hebrew) | no | no | no | no | no | partial | poor (reviews) | **yes, shaped + bidi** |
| Indic scripts | no | no | no | no | partial | partial | partial | **yes** |
| Windows first-class | ported by users | partial | buggy | partial | yes (npm) | partial | web | **yes, CI-tested** |
| Doctor with fix commands | no | partial | partial | yes | yes | partial | n/a | **yes, 3 OS** |
| No-terminal path | no | no | no | no | no | no | yes (web) | **app zip + Codespaces** |
| Commercial use of the tool | ❌ NC | ❌ NC | ✅ | ✅ | ✅ | AGPL | paid | **✅ MIT** |
| Series mode with variation | no | no | no | no | no | partial | yes (repetitive) | **yes, variation-checked** |
| Channel style file | no | partial | no | no | partial | partial | brand kit | **yes** |
| Policy defaults (disclosure reminder, anti-repetition) | no | no | no | no | partial (TikTok flag) | no | no | **yes** |

## 2. Top 20 user problems (with evidence)

1. Non-developers can't run the tools; they post video ideas as issues — explainroo #44, #47; opuscar #12, #13, #27, #32 and ~15 more; OpenMontage #97, #113, #694.
2. Windows paths/junctions crash setup — cinecode #4; opuscar #28.
3. Windows file locks (EBUSY) on rename — cinecode #5.
4. Windows: local server refuses Chrome's parallel loads → render hangs — huashu-art-motion #3.
5. Windows: console window per render, credential dialogs — HyperFrames #3430, #4702.
6. Commercial use blocked by NC licences — anything2explainer #5, #6, #12, #22; video-talkcraft #43, #46; onetake #3, #4, #13.
7. Low-memory machines crash (hard-coded concurrency) — anything2explainer #20.
8. No checkpoint/resume for long jobs — OpenMontage #129, #414.
9. Long-video caption/frame errors — OpenMontage #433 ("No frame found at position 5546").
10. Repeated full re-renders burn quota/time — video-talkcraft #24.
11. Agents refuse clone-and-run setup scripts — opuscar #24; self-update without consent — HyperFrames #2613.
12. Install fails at first hurdle — HyperFrames #407; OpenMontage #18, #19.
13. Fake installers/malware exploiting demand for a one-click app — OpenMontage #175, #444, #626.
14. ffmpeg version edge cases hang or truncate audio — cinecode #12; opuscar #7; onetake #8.
15. Washed-out / shifted colours (range conversion) — opuscar #62; onetake #7.
16. Arabic text renders as isolated, reversed letters — HyperFrames #5885; InVideo Trustpilot review on Arabic quality.
17. Portrait breakage from hard-coded 1920×1080 — huashu-art-motion #9, #10, #11.
18. "Every AI video looks the same" — OpenMontage #202 (also the YouTube demonetisation risk).
19. Paid generative APIs required for core visuals — vox-director #19 (local port); OpenMontage #961 (keyless search).
20. Skill too big to install in some clients — huashu-art-motion #15 (32 MB).

Paid-product complaints (Trustpilot/review sites): videos stuck processing, credits burned on failed renders, hidden renewals, weak non-English (Arabic) output, auto-posting linked to channel terminations.

## 3. Quality bar (described, never copied)

docuframe outputs must match or beat these reference qualities:

1. **Evidence-board long take:** one continuous camera across a designed wall of photos, clippings and cards; strings/routes lead the eye; each stamp or highlight lands on the spoken word. No slideshow cuts.
2. **Editorial paper collage:** torn-paper cutouts, halftone photos, hand-set type; parallax between layers; nothing generated.
3. **Big-studio flat explainer:** limited palette, bold geometric icons, kinetic type, eased motion (no linear tweens), consistent stroke weights.
4. **Archive documentary:** slow camera moves on period photos with grain and vignette, licence line visible, typewriter captions, period maps.
5. **Data-led map story:** borders changing by year, animated routes with a moving marker, labelled cities, legend, source line; numbers count up to a sourced value.
6. **Newsroom bulletin:** lower thirds, ticker, quote cards with attribution and date.
7. **Dark briefing room:** dark UI panels, scan lines, coordinates, redaction bars for case-file reveals.
8. **Retention craft:** hook stating the payoff inside 10 seconds; a visual change every 4–8 s; a pattern interrupt every 30–60 s; chapter cards matching description timestamps.

Craft rules collected (YouTube editing guides; designer guides): most drop-off happens in the first 30–60 s; the opening must confirm the title/thumbnail promise; B-roll shots 3–8 s; over-cutting fatigues; consistency of fonts, colours and transition types is what reads as "professional"; eased motion, not abrupt starts/stops; avoid the "appear → fade → hold → fade" slideshow pattern.

## 4. Gaps docuframe fills (ranked by how often users asked)

1. Runs for non-developers (no terminal; zip upload; Codespaces) — most frequent.
2. Windows that works — second.
3. Commercial use, clearly stated, with attribution manifest — third.
4. Long, memory-safe, resumable renders with ETA.
5. Safe install (no remote-code bootstrap, no silent self-update; signed releases; warn about fake installers).
6. RTL and Indic typesetting.
7. Distinct-looking outputs + variation (anti-sameness, anti-demonetisation).
8. Fully local (no paid APIs, no keys) by default.
9. Documentary-grade sourcing: fact sheet, on-screen sources, licence lines.
10. YouTube package and dubbing.

## 5. Licence & policy summary

- Default engine must be fully free: **not Remotion** (company licence above 3 employees), **not GSAP** in core (fee-based end-user products need a paid licence). See `licences.md`.
- Local voice: Kokoro (Apache-2.0) — but non-English phonemes depend on espeak-ng (GPL-3.0). Piper is now GPL-3.0. **Owner decision needed** on how we ship espeak-ng.
- Platform defaults: anti-repetition variation, human approval recorded, AI-disclosure checklist in the YouTube package, no AI personas on sensitive topics. See `platform-policies.md`.

## 6. Still to research before launch (honest list)

- Deeper Reddit/HN/X threads from documentary creators (only blog/guide sources read so far).
- Paid-product feature/pricing matrix beyond review-site complaints.
- Per-language wav2vec2 alignment model licences.
- Skia shaping for Urdu Nastaliq, Hebrew, Bengali, Tamil, CJK vertical punctuation (Persian, Arabic, Hindi passed the spike).

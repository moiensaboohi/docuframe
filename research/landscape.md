# Landscape — narrated documentary and explainer skills

Researched 2026-11-20. GitHub search API (25 queries × sort by stars and by updated, 511 unique repos), plus shallow clones of the 17 most relevant repos. Star counts are as of that day. Issue data comes from the GitHub issue search API, sorted by reactions and by comments.

> Note on naming: this is a research file. Other projects are named here only so the research can be checked. Per the build rules, no other project name appears in code, docs or commits outside `research/` and `THIRD_PARTY_NOTICES.md`.

## 1. The field at a glance

| Repo | Stars | Forks | Licence (verified from LICENSE file) | Created | Last push | What it makes |
|---|---:|---:|---|---|---|---|
| OpenMontageInc/OpenMontage | 81.7k | 11.1k | AGPL-3.0 | 2026-03 | 2026-11-16 | Everything: 12 pipelines, 100+ tools, 141 SKILL.md files. Mostly generative video. |
| Vincentwei1021/video-shotcraft | 21.7k | 2.0k | Apache-2.0 | 2026-07 | 2026-11-19 | Product promos in Remotion; 124 shot recipe cards. Not narrated docs. |
| lemomo-ai/lemo-opuscar | 18.7k | 2.4k | Mixed: code MIT, docs CC-BY-NC-4.0, films CC-BY-4.0 | 2026-09 | 2026-11-17 | 99 code-made film styles; a style library more than a pipeline. |
| alchaincyf/huashu-art-motion | 7.3k | 0.7k | MIT | 2026-10 | 2026-11-18 | 35 art styles, 9 narration grammars; Chinese-first. |
| feitangyuan/onetake | 4.3k | 0.3k | PolyForm Noncommercial 1.0.0 | 2026-09 | 2026-11-19 | Short product films, one continuous camera, no cuts. |
| Vincentwei1021/anything2explainer | 3.4k | 0.4k | PolyForm Noncommercial 1.0.0 | 2026-09 | 2026-11-19 | Topic → black-background MG explainer (Remotion), zh/en. |
| Alisa0808/vox-director | 3.0k | 0.4k | MIT | 2026-07 | 2026-10-05 | Paper-collage explainers via a paid generative API + ffmpeg. |
| sarpstar/cinecode | 2.8k | 0.5k | MIT | 2026-11 | 2026-11-12 | Films, ads, explainers in code (HTML + three.js), 5k-word SKILL.md. |
| Vincentwei1021/video-talkcraft | 2.4k | 0.2k | PolyForm Noncommercial 1.0.0 | 2026-08 | 2026-11-19 | Voiceover-driven explainers (Remotion), word timestamps on CPU. |
| vincentsch/explainroo | 1.4k | 0.1k | MIT | 2026-09 | 2026-11-18 | npx CLI; local Kokoro voice; node-canvas; many languages; posting. |
| Moh4696/cinematic-skill | 0.8k | 0.1k | MIT | 2026-11-09 | 2026-11-09 | One continuous camera over a designed "evidence board"; Skia (Python). |
| sitor-ai/frametell | 0.5k | 0.1k | AGPL-3.0 | 2026-10 | 2026-11-19 | Explainer "director agent". |
| sirioberati/YouTube-AI-Motion-Graphics | 0.2k | — | MIT | 2026-10 | 2026-10-27 | 74 HTML explainer boards synced to a presenter's words; NLE timeline export. |
| staryone/motlab | 0.2k | — | MIT | 2026-11-16 | 2026-11-19 | Canvas scenes rendered with WebCodecs in headless Chrome. |
| scosman/videowright | 0.2k | — | MIT | 2026-05 | 2026-11-02 | HTML/CSS/JS segments + timeline + dev server. |
| BubbleBrainBB/BB-Video | 0.2k | — | MIT | 2026-10 | 2026-11-12 | 37 visual styles, pure `renderFrame(t)` in Chrome. |
| iart-ai/explainer-video-skills | 0.1k | — | MIT | 2026-06 | 2026-11-11 | Script, storyboard, render; year-in-review. |
| haiderfarooq3/khan-explainer | 0.2k | — | MIT | 2026-10 | 2026-10-11 | Pen-drawing explainers, local. |
| SunandBean/paper2video | 54 | — | MIT | 2026-10 | 2026-11-10 | arXiv paper → fact-checked explainer with verification report. |

Adjacent but not competitors: Remotion (React video framework, custom licence), HyperFrames (Apache-2.0, HTML + GSAP video framework, 700+ issues), KrillinAI/OpenCreator (dubbing, 120+ languages), TubeLab youtube-research-skills (topic research only).

**Nobody owns "documentary" yet.** The big repos are general (OpenMontage), style libraries (opuscar), or product promos (shotcraft). The direct documentary/explainer skills are all under 3.5k stars, and the two most-starred narrated-explainer skills (anything2explainer, video-talkcraft) are noncommercial — their users keep filing commercial-licence requests (see §3).

## 2. Per-repo notes (direct competitors)

### anything2explainer — PolyForm NC (study only)
- **Promise:** topic in → black-background motion-graphics explainer with voice, captions, chapter progress bar. zh/en.
- **Pipeline:** script → voice → storyboard → Remotion scenes → render, with **four hard user-approval stops**, a multi-agent split, and a QC rubric against one reference film.
- **SKILL.md:** 809 words, Chinese, short; detail in `reference/`. Fixed single look.
- **Strong:** clear checkpoints, one strong look, worked sample film to compare against.
- **Weak:** one style; noncommercial; Remotion-only; render concurrency hard-coded (issue #20, low-memory crash); Windows needs a PowerShell port (issue #16).

### video-talkcraft — PolyForm NC (study only)
- **Promise:** Chinese voiceover script + finished narration → word timestamps on CPU → "SHOTBOOK" storyboard → Remotion film.
- **Strong:** semantic tagging of each sentence (new elements only on meaning boundaries, not one element per sentence); machine gates for layout rotation and asset coverage; live "workbench" preview; 108 motion recipe cards.
- **Weak:** heavy (16 Remotion packages + GSAP + Playwright + three); noncommercial; issue #24 — the agent re-rendered the whole film 9 times and burned the user's quota, because "cost discipline was prose, not a machine gate".

### cinecode (sarpstar) — MIT
- **Promise:** short films, long YouTube videos, ads, explainers, music videos from code; Quick mode (one HTML file + Web Audio) and Film mode (six gated steps).
- **SKILL.md:** 5,096 words; uses a `UserPromptSubmit` hook.
- **Strong:** two modes (exactly the quick/director split we need); style frame → animatic → render gates.
- **Weak (issues):** Windows `PermissionError` on the "Application Data" junction (#4), `EBUSY` on file rename with no retry (#5), ffmpeg 7 `apad` hang (#12), sound pack downloads broken (#6).

### cinematic-skill (Moh4696) — MIT
- **Promise:** narrated cinematic film from code; **one continuous camera over one designed world** (photos, documents, cards, maps with routes, big numbers), every hit timed to the narrator's word.
- **Stack:** Python, skia-python, numpy, pillow, ffmpeg. Light install. Scripts for Commons fetch, maps, beats, captions, SFX, mix.
- **SKILL.md:** ~1,480 words, rules written "from what broke"; explicit self-review list of bugs found in stills.
- **Strong:** the closest thing to our "cinematic evidence board" style; deterministic; light; archive licence fetching.
- **Weak:** one world style plus a light studio look; no YouTube package, no RTL, no chunked/resumable long render documented, one week old.
- **Decision (2026-11-20):** third-party project. Studied for ideas only; docuframe's engine and pipeline are written independently (see `tools/provenance_check.py` results in `evals/RESULTS.md`).

### vox-director — MIT
- **Promise:** topic → paper-collage explainer, but via a **paid generative API** for keyframes and motion.
- **Weak:** core visuals are generated (fails our deterministic rule); issue #19 is someone porting it to local rendering because users don't want paid media APIs.

### explainroo — MIT
- **Promise:** explainer MP4 with a local voice (kokoro-js), no API key; `npx --yes explainroo`.
- **Strong:** lightest install in the field (npm only, no Python); 8+ narration languages; app recording; posting partner; clear news/changelog; website with videos.
- **Weak:** explainer/demo focus, not documentary; no RTL; demo media 403s (#45); people post video *ideas* as issues (#44 "Videos ia", #47 "Videos GTA6") — they can't run it.

### onetake — PolyForm NC (study only)
- Single HTML composition, pure functions of time, "never cut to the next slide". Issues: render truncated to the shortest sound file (#8), colour shift on playback (#7, colour range), continuity check fooled (#6). Two commercial-licence requests.

### lemo-opuscar — mixed licence
- 99 styles as docs + demo code. **Docs are CC-BY-NC-4.0** (study only); code MIT. Issues: setup.sh refused by agents as remote code execution (#24), Windows venv path bugs (#23, #28), loudnorm under-reporting duration (#7), double limited-range conversion → washed-out films (#62). Most issues are people posting song links and video wishes — non-developers who can't run it.

### OpenMontage — AGPL-3.0 (study only)
- Huge. Issues show: checkpoints and resume requested (#129) and not enforced (#414); "every AI video looks the same" (#202); Remotion caption burn fails on long videos (#433); zero-key local path broken, Piper falsely reported available (#237); **malware typosquats distributing fake Windows installers** (#175, #626, #444) — people want a click-to-run app and get scammed; Docker build requested (#384); tutorial video requested (#150).

### huashu-art-motion — MIT
- Windows: single-threaded local HTTP server refuses Chromium's parallel loads → render never finishes (#3). Chunked parallel render "3× faster" (#8). Hard-coded 1920×1080 centres break portrait (#9–#11). Skill directory 32 MB / 507 files exceeds install limits (#15).

### HyperFrames (engine, Apache-2.0) — the most common engine bugs
- Install failed at first hurdle (#407); CLI hangs on calibration (#1231, 33 comments); WSL2 falls back to SwiftShader (#5548); visible console window per render on Windows (#3430); **Arabic per-letter splits render isolated letters and reversed rows (#5885)**; frames depend on previous frame across workers (#7111); font height compressed (#1090).

### Remotion (engine)
- Custom licence: free for individuals, ≤3-employee companies, non-profits; Company Licence otherwise (see `licences.md`). Long-standing "License is not permissive" issue (#17).

## 3. What the issues say (the strongest signal)

Ranked by how often the theme appears across repos:

1. **Can't run it at all / posts video ideas as issues** — explainroo #44 #47, opuscar #12 #13 #27 #32 #41–#59, OpenMontage #97 #113 #694, vox-director #17. Non-developers are the majority of the audience.
2. **Windows breaks** — cinecode #4 #5, huashu-art-motion #3, opuscar #23 #28, anything2explainer #16, HyperFrames #3430 #4702 #5548.
3. **Commercial use unclear or forbidden** — anything2explainer #5 #6 #12 #22, video-talkcraft #43 #46, onetake #3 #4 #13. Creators want to monetise; NC licences block them.
4. **Memory / long renders / resume** — anything2explainer #20, OpenMontage #129 #414 #433, huashu-art-motion #8.
5. **Install friction and trust** — opuscar #24 (agents refuse clone-and-run), HyperFrames #407 #2613, OpenMontage #18 #19, fake installers #175 #626.
6. **Audio/encode edge cases** — ffmpeg 7 `apad` hang (cinecode #12), loudnorm duration (opuscar #7), truncation to shortest audio (onetake #8), colour range double conversion (opuscar #62, onetake #7).
7. **RTL text broken** — HyperFrames #5885; no competitor handles Arabic/Persian shaping in its own pipeline.
8. **Cost/quota burn from repeated full renders** — video-talkcraft #24.
9. **Sameness** — OpenMontage #202 "every AI-generated video looks the same" (also a YouTube monetisation risk).
10. **Wants local / no paid APIs** — vox-director #19, explainroo #43 (local voice cloning), OpenMontage #961 (keyless search).
11. **Wants a tutorial / desktop app / Docker** — OpenMontage #150 #384, HyperFrames #5504.
12. **Install size** — huashu-art-motion #15 (32 MB skill dir too big for a client).

## 4. README patterns of the winners

- First screen: name, one-line promise, a video or animated WebP **above install**.
- One copy-paste line ("Tell your agent: …" or `npx …`), then collapsible alternatives.
- A gallery with the prompt under each output.
- News/changelog block (explainroo) signals momentum.
- Honest limits section is rare — an opening for us.
- None publish a benchmark against others.

## 5. Gaps nobody fills well

- Documentary-specific pipeline with a **fact sheet and per-claim sources**, and on-screen source lines.
- **YouTube package** (titles, description with sources and chapters, thumbnails, tags).
- **RTL and Indic** typesetting done right in the renderer.
- **Commercial-safe licence** + per-asset attribution manifest.
- **Resumable chunked render** with memory cap and ETA, measured on 16 GB.
- **Dubbing** the same project into other languages with re-timing.
- **Series mode** with variation built in (against repetitive-content demonetisation).
- **A no-terminal path** that actually works (Claude app zip + Codespaces).

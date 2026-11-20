<h1 align="center">docuframe</h1>

<p align="center"><b>Give it a topic or a script, get a finished documentary or explainer film in the style you pick.</b></p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-24292f" alt="MIT">
  <img src="https://img.shields.io/badge/agents-Claude%20Code%20·%20Codex%20·%20Cursor%20·%20Gemini%20CLI%20·%20OpenCode-24292f" alt="agents">
  <img src="https://img.shields.io/badge/version-0.1.0%20preview-orange" alt="version">
</p>

<p align="center"><img src="docs/media/hero-stills.jpg" alt="Three frames made by docuframe: a big sourced number in English, a Persian title set right to left, and a Hindi vertical short with two comparison cards"></p>
<p align="center"><sub>English 16:9 · Persian right-to-left · Hindi 9:16 — same project format, same engine. (Hero video lands with the first release.)</sub></p>

## Install

```
npx skills add moiensaboohi/docuframe
```

Then ask your agent: *"Make a 3 minute documentary about the Great Molasses Flood."*

<details><summary>Claude Code plugin marketplace</summary>

```
/plugin marketplace add moiensaboohi/docuframe
/plugin install docuframe@docuframe
```
</details>

<details><summary>Codex, Cursor, Gemini CLI, OpenCode</summary>

The repo ships `.codex-plugin/`, `.cursor-plugin/`, `gemini-extension.json` and `AGENTS.md`.
Or copy `skills/docuframe` into your agent's skills folder. The engine is a Python package:
`pip install "git+https://github.com/moiensaboohi/docuframe"` (the skill tells you if it is missing).
</details>

<details><summary>Claude app (no terminal)</summary>

Download `docuframe-skill-<version>.zip` from Releases and upload it as a skill. The engine is bundled
inside. Where the app can run code, it renders there; otherwise use the cloud option below.
</details>

<details><summary>One click in the browser (no installs)</summary>

Click **Code → Codespaces → Create codespace**. Python, ffmpeg, the engine and the local voice are
preinstalled; open `docs/START-HERE.md`.
</details>

First run on your machine: `docuframe doctor` checks everything and prints the exact fix for
Windows, macOS or Linux.

## Ask it like this

> "Make a 2 minute documentary about the Great Molasses Flood of 1919."

> "Turn this script into a YouTube explainer with sources and chapters. Let me approve the stills first."

> "Here's my script and my recording, make the video in 16:9 and a 9:16 short."

> "یک مستند کوتاه درباره‌ی کانال سوئز بساز."

> "Dub last week's episode into Spanish."

## What you get

- the film (16:9 up to 30 min; 9:16 and 1:1 cut from the same project)
- SRT and VTT captions that match the narration word for word
- a YouTube package: 3 titles, a description with chapters, sources and image credits, tags, 3 thumbnails, an upload checklist
- `manifest.json`: every source, image licence, font and voice, and the one command that re-renders it

## How it works

1. **Research** — the agent writes a fact sheet: every claim with its sources. No source, no claim.
2. **Script** — hook in the first 10 seconds, chapters, numbers written the way they're spoken.
3. **Voice** — a free local voice, your own recording, or any TTS you have a key for.
4. **Beats** — `film.json`: each beat a scene (photo, map, quote, big number, timeline…) that lands on a spoken word.
5. **Approval stills** — one frame per beat; the agent reviews them, you can too.
6. **Render** — drawn by code (Skia), in resumable chunks with an ETA; runs on a 16 GB laptop.
7. **Check and package** — legibility, safe areas, sources, licences, captions, chapters; then the YouTube package.

## Styles

| Style | For |
|---|---|
| `evidence-board` — one camera over a cork wall of pinned photos, string and stamps | true stories, history, crime |

More packs ship as data (`styles/<name>/style.json`) — see the roadmap and `community-styles/`.

## Languages

Text is shaped with HarfBuzz and ICU: Arabic, Persian, Urdu and Hebrew join and run right to left;
Hindi, Bengali and Tamil conjuncts form; Chinese and Japanese captions break per character.
The local voice is native in English, Spanish, French, Hindi, Italian, Portuguese, Japanese and
Chinese; for other languages use your own recording (other languages work as accented drafts).

## Honest limits (0.1 preview)

- One style pack so far. Map scenes need map data built with `docuframe map`.
- Rendering is CPU-only. On a 2-vCPU cloud VM a 1080p frame takes ~0.3 s per worker; a 4-core laptop runs 3 workers.
- Word timing without `docuframe align` is estimated from letter counts (~150–250 ms).
- Archive search covers Wikimedia Commons; other archives need the item link and its rights line.
- The comparison benchmark against other skills and the Windows/macOS first-run timings are not published yet.

## You own what you make

The code is MIT. **Everything you make with docuframe belongs to you and may be used commercially**,
subject only to the attribution lines of the images, maps or fonts you chose — the skill writes those
into your description and `manifest.json` for you. No watermark, ever.

The default engine path is entirely free and permissively licensed (no per-seat or company licence).
Third-party licences: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Platform rules it follows for you

YouTube does not monetise channels whose videos look template-made or mass-produced, and asks you to
disclose realistic synthetic content. docuframe varies layouts between episodes, records your
approvals, keeps everything on screen code-drawn and sourced, and puts an upload checklist in every
package. (Rules checked 2026-11-20; see `research/platform-policies.md`.)

## Update

`npx skills add moiensaboohi/docuframe` again, or `git pull` in your clone. See [CHANGELOG.md](CHANGELOG.md).

## License

MIT © Moein Saboohi

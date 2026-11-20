# Changelog

## 0.1.0 — unreleased
- Engine: Skia film engine (one continuous camera or hard cuts), shaped text for every script
  (RTL, Indic, CJK), data-driven scenes (film.json), style packs as data.
- Pipeline: local voice, own recording, word alignment, chunked resumable render with ETA,
  SRT/VTT captions, self-review checks, YouTube package, manifest.
- Sound: effects synthesised in code from the film's cues; mix with ducked music and -14 LUFS.
- Captions: cues break at pauses within on-screen time and length limits; burned-in captions via one ffmpeg overlay pass.
- Styles: 15 packs — evidence-board, editorial-collage (paper cut-out), flat-explainer, minimal-mono,
  archive-documentary, briefing-room, vintage-atlas, newsroom, case-file, lab-notebook, tech-gradient,
  pastel-pop, bold-poster, cinematic-dark, riso-print. Skins (panel, photo, title, number, motion,
  accents, ground, camera feel) are data, so new looks need no engine code. `tools/make_styles.py`
  regenerates the built-in packs.
- Tested inputs: English history short (16:9), Persian right-to-left (16:9), Hindi vertical (9:16).

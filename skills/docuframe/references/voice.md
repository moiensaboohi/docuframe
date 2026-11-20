# Voice and timing

| path | command | notes |
|---|---|---|
| local voice | `voice --project P [--voice am_michael]` | Kokoro (Apache-2.0), offline after a 120 MB download. Native: en-us, en-gb, es, fr, hi, it, pt-br, ja, zh. `voice --list` shows voices. |
| experimental languages | same, with `lang` ar, fa, ur, he, bn, ta, de | read through espeak-ng phonemes: accented. Drafts and timing only. |
| user's recording | `voice --project P --audio read.wav` | split into lines by pauses; if a cut is wrong, force it in `audio/overrides.json` `{"cut_before": {"7": 41.2}}` |
| system voice | `voice --engine system` | macOS `say`, Windows SAPI, Linux espeak-ng |
| any TTS | `voice --engine cmd --cmd 'tts --in {txt} --out {out}'` | cloud TTS with the user's own key goes here |

Then `narration` (trims, gaps, -16 LUFS, `audio/timing.json`) and optionally `align`
(faster-whisper, MIT; word starts within ~50–80 ms). The espeak-ng phonemizer used by the local voice
for non-English text is GPL-3.0 and is installed on the user's machine by pip, never bundled.

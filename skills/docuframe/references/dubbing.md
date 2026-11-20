# Dubbing a film into another language

1. Copy the project folder (`my-film` → `my-film-es`). Delete `audio/` and `out/`.
2. Translate `script.json`: keep every line `id`, `facts` and chapter; translate `text`, write
   `spoken` with numbers in words; set `"lang"`.
3. Translate on-screen text in `film.json` (`text`, `sub`, `caption`, `label`, `title`, quote `text`
   only if a published translation exists — otherwise keep the original and add a translated `sub`).
   Update every `at` word to a word in the new `spoken` text. Set `"lang"` (drives fonts, RTL, source labels).
4. `voice` → `narration` → `align` → `render --stills auto` → review → `make --yes`.
Timing follows the new narration; right-to-left text is shaped and placed automatically.

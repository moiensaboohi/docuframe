# Community style packs

A style is data, not code: a folder with

```
community-styles/<your-style-name>/
  style.json   # tokens (colours, fonts), finish (board, grade, grain), camera, layout, scene defaults
  rules.md     # what it is, when to use it, how to judge a still
  stills/      # 3+ stills rendered by docuframe from a template, 960x540 JPG
```

Copy `skills/docuframe/styles/evidence-board/style.json` as a start. Rules for a pack to be merged:

1. Describe the look in its name ("riso newsprint", "night atlas") — never a channel, studio, brand
   or person's name.
2. Fonts only from `core/docuframe/fonts.py` REGISTRY (openly licensed) or system defaults.
3. Board textures are generated: `"board": "flat-R-G-B.png"` or a built-in texture name.
4. Render the stills with `python tools/run_fixture.py history-short` after setting the style, and
   run `docuframe check`: no ✗.
5. Open a pull request with the stills in the description.

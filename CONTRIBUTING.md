# Contributing to docuframe

Thanks for helping. The most useful contributions, roughly in order:

1. **A film you made.** Open a Discussion or an issue with the link and the style you used. Real films
   show what breaks, and the best ones go in the README gallery.
2. **A style pack.** Styles are data, not code: a `style.json`, a `rules.md` and three stills in
   `community-styles/<your-style>/`. Copy the closest built-in pack from `skills/docuframe/styles/`,
   change it, and render the showcase with `python tools/style_gallery.py evals/fixtures/showcase out.jpg your-style`.
   Give it your own name; never name a style after a real studio, channel, brand or person.
3. **A template.** A worked project (`script.json`, `facts.json` with real sources, `film.json`) in
   `skills/docuframe/templates/`. Every fact needs a source a reader can open.
4. **A language.** Test a film in your language and report shaping, line breaks, numerals, captions
   and voice. Right-to-left and Indic scripts especially.
5. **Bugs.** Include your OS, `docuframe doctor` output and, if a render looked wrong, `out/check.md`
   and a still from `out/stills/`.

## Setup

```
git clone https://github.com/moiensaboohi/docuframe && cd docuframe
pip install -e ".[all]"
docuframe doctor
python tools/run_fixture.py history-short fa-rtl hi-vertical   # must pass before a pull request
```

## Rules that keep the project healthy

- Only permissive dependencies (MIT, BSD, Apache, ISC; OFL for fonts). No GPL/AGPL/non-commercial code.
- Every user-facing error says what happened and the one thing to do next.
- Read `skills/docuframe/references/design.md` before touching a style: one accent colour, no gradient
  text, no glow, no emoji, no stock phrases. `docuframe check` flags these as `slop`.
- Windows is first-class: UTF-8 everywhere, subprocesses through `docuframe.util`.
- Never add a feature that invents facts, imitates a real person's voice without consent, or makes
  generated footage look like real archive.

By contributing you agree your contribution is released under the MIT licence.

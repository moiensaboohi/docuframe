# AGENTS.md — working in the docuframe repository

docuframe is an agent skill that turns a topic or script into a documentary/explainer film.
The skill an end user's agent follows is `skills/docuframe/SKILL.md`; this file is for agents
changing the repo.

## Layout
- `core/docuframe/` — the Python package (engine, scenes, voice, render, checks, package). No style
  names in here: styles are data.
- `skills/docuframe/` — SKILL.md, references, `styles/<name>/` (style.json + rules.md + stills),
  `templates/` (worked projects), `scripts/` (launcher, doctor wrappers).
- `community-styles/` — contributed style packs (data only).
- `evals/` — prompts, fixtures, scoring; `evals/RESULTS.md` is the record.
- `research/` — landscape, licences, platform policies, decisions. Read `research/decisions.md`
  before changing the engine.

## Rules
- Our names only. Another project's name may appear only in `THIRD_PARTY_NOTICES.md` and `research/`.
- Only permissive dependencies (MIT, BSD, Apache, ISC, OFL for fonts). Record new ones in
  `THIRD_PARTY_NOTICES.md` and `research/licences.md`. Never vendor GPL/AGPL/NC code.
- Every file read/write uses `encoding="utf-8"`; every subprocess goes through `docuframe.util`
  (no console windows on Windows, plain-language errors); renames use `replace_with_retry`.
- Every user-facing error says what happened and the one thing to do next.
- Test on three inputs before merging engine changes:
  `python tools/run_fixture.py history-short fa-rtl hi-vertical` and look at the stills.

## Commands
```
pip install -e ".[all]"
docuframe doctor
python tools/run_fixture.py history-short   # voice → stills → check, prints the sheet path
python tools/make_styles.py                # rewrite the built-in style packs from its table
python tools/style_gallery.py PROJECT out.jpg [styles]   # one project in many styles, one row each
python tools/make_banner.py PROJECT        # README banner: one style per scene type (project: evals/fixtures/showcase, voiced)
python tools/brand.py                      # logo files (docs/media/logo): the custom frame-built wordmark
```

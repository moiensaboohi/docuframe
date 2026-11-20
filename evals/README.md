# Evals

`prompts.json` holds the eval prompts (every mode and input type, five languages, edge cases, two
will-not-do requests). `fixtures/` holds projects for engine tests that need no research.

## Automated checks (per film)
`docuframe check` covers: facts linked and sourced, data beats sourced, image licences, timing
method, pacing, legibility (≥ 28 px at 1080p), framing and 9:16 safe areas, blank frames,
captions word-for-word, YouTube chapter rules. CI (`.github/workflows/ci.yml`) runs a first-run on
Windows, macOS and Linux (paths with spaces and Persian letters), a forced-stop resume, and the RTL
and Indic fixtures.

## Human rubric (blind, 1–5 each)
1. Looks professional (consistency, motion, type)  2. Story and pacing  3. Accuracy and sourcing
4. Legibility  5. Sound  6. Would publish as is.

## Not automated yet
Graphics-to-word timing within ±80 ms needs aligned audio (`docuframe align`) and is measured on CI
where model downloads are allowed. The blind non-technical tester and the comparison benchmark are
in `RESULTS.md` once run.

# Design rules: make it look made, not generated

Read this before writing `film.json` and before changing or making a style. `docuframe check`
flags the mechanical parts of it (see the end); the rest is judgement, and it is your job.

The test for every frame: would a good human motion designer have made this choice on purpose?
Generated-looking work comes from defaults nobody chose. Every rule below replaces a default
with a decision.

## Colour
- One accent colour per film, used for one job (the thing to look at). Everything else is the
  ground, the text colour and one muted grey.
- No gradient text. No purple-to-blue, pink-to-orange or "aurora" gradients anywhere. No rainbow
  colour blobs. A flat colour is almost always the better choice; if a surface needs depth, use a
  real photograph or a quiet shadow.
- No glow, neon edges or bloom unless the subject is literally light (a city at night, a screen).
- Don't reach for violet because it says "tech". Pick the accent from the subject: a brick red
  for a fire, the green of a banknote, the blue of a uniform.

## Type
- Small and confident beats huge and shouting. A headline should not span the frame edge to edge.
- Sentence case for headlines and labels. ALL CAPS only for a short label of 1–3 words.
- One typeface family, two at most (a serif headline with a sans body is fine).
- No emoji, no decorative symbols (✨ 🚀 ⚡ → ✓) in on-screen text.
- Numbers keep their unit and precision honest: "2.3M gal", not "2,300,000+!!".

## Words on screen
On-screen text is the shortest true version of what the narration says, taken from the facts.
Never write filler a viewer has seen a thousand times:
- "Did you know…?", "Let's dive in", "Here's the thing", "In a world where…", "The untold story",
  "You won't believe", "Mind-blowing", "Game-changer", "Revolutionary", "Unlock", "Unleash",
  "Delve", "Journey", "Tapestry", "Testament to", "Ever-evolving", "Navigating the…",
  "Not just X, but Y", "It's not about X, it's about Y".
- No exclamation marks in titles or labels. Let the fact be the surprise.
- No rhetorical question as every chapter title.

## Layout and motion
- One idea per beat; give it room. Empty space is part of the design, not a gap to fill.
- Don't add shapes, sparkles, floating dots or corner brackets that mean nothing. Every mark on the
  frame points at, frames or measures something.
- Pick one alignment for the film (start or centre) and keep it.
- Motion lands on the spoken word, settles and holds. No constant floating, pulsing or spinning.
- Glass only over something worth blurring (the film's own photographs); never glass on glass.

## Images
- Real, sourced photographs over generated pictures. Never put AI-generated images in a
  documentary as if they were real, and never generate pictures of real people or events.
- Don't stack effects on photos (duotone + grain + glow + vignette). One treatment, from the style.

## What `docuframe check` flags
- `slop` warnings: emoji, exclamation marks and stock phrases in on-screen text; titles in ALL
  CAPS longer than three words; gradient text or gradient grounds turned on in a style; more
  than two accent hues; glow above a light touch.
Treat each one as a question: is this a decision, or a default? Fix it unless you can answer.

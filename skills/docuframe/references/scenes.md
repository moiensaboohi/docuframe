# Scene library (film.json beats)

Every beat: `scene` (below), `line` (narration line id), optional `at` (spoken word it lands on;
`"word#1"` = second occurrence; a number = seconds after the line starts), optional `source`
(shown on screen while the beat is up and listed in the description). Beats are laid out in one
world (style camera `world`) or cut between (`cuts`); vertical formats stack clusters in a column.

| scene | fields | use it for |
|---|---|---|
| `title` | `text`, `sub`, `size` | the opening title / hook card (auto-fits the frame) |
| `chapter` | `title`, `number` | a chapter card; also becomes a YouTube chapter |
| `photo` | `photo` (id), `label`, `mark` {kind ellipse/underline/arrow/highlight, fx, fy, w, h, at}, `w` | archive photo with pin, name bar, pen mark on the spoken word |
| `document` | `text` + `phrase` + `mark_at` (typeset recreation) or `photo` | a letter, clipping or record with the key phrase highlighted |
| `quote` | `text` (verbatim), `who`, `when` | a quote card (RTL quotes get « ») |
| `big-number` | `value` (number rolls up; string shown as is), `prefix`, `suffix`, `caption` | one statistic, always with `source` |
| `timeline` | `events` [{`when`, `label`, `at`}] | dates that tick on as they are spoken |
| `comparison` | `left`/`right` {`title`, `lines`} | two sides; stacked in vertical formats |
| `list` | `title`, `items` [{`text`, `at`}], `numbered` | steps, causes, results |
| `map` | `map` (name from map.json via `docuframe map`), `fill` [regions], `pins` [{`lon`, `lat`, `label`, `at`}], `routes` [{`points` [[lon, lat], …], `label`, `label_at` (0–1 along the route), `label_side` (1 right, -1 left), `line`, `at`, `dur`, `color`, `dashed`}], `scale` (optional; the map fits the frame by default) | places, borders, where it happened, trade and travel routes |
| `lower-third` | `name`, `role`, `until` | name a person on screen (overlay) |
| `end` | `text`, `sub` | closing card; the camera pulls back over the whole world under it |

Pacing targets (style `pacing`, checked by `docuframe check`): a new beat every 4–8 s; a pattern
interrupt (chapter, map, quote, big number) every 30–60 s; the hook inside 10 s. A beat shorter than
1.5 s can't be read: anchor it earlier or merge it.

Legibility (checked): text introduced in a beat must be ≥ 28 px tall at 1080p; in 9:16 nothing in
the bottom 20 % or top 10 % (app buttons and captions sit there).

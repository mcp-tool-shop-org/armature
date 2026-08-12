# Wan video prompt guide — distilled notes (official-docs translation)

**Provenance.** Retrieved by the Director on 2026-08-12 as `Wan_AI_Prompt_Guide_EN.md`,
self-described "Translated and compiled from official DingTalk Alidocs developer
documentation for Wan AI." Form: a compact translation/compilation — undated, no
byline — the closest document to the official video prompt guide this repo has held;
the raw DingTalk original stays reachable via the Director's proven export path if
byte-fidelity ever matters. This closes the admin-shelf item. It supersedes
`docs/wan21-prompt-guide-notes.md` as the primary video-prompting reference; the 2.1
rendition is kept for its fuller camera/atmosphere/style vocabulary.

**Version scope.** The core formulas are stated Wan-generic; §3 below is explicitly
Wan 2.6+. Our routes run 2.2 tiers. Per the posture's dated-field-check rule,
everything here is **ADVISORY until measured on the tier that would use it**, and 2.6+
features are knowledge, not admission — no 2.6 variant has a licence-map row.

## The formulas (as the document states them)

- **Four-part order, explicit:** `[Subject] + [Specific Action] + [Camera Movement] +
  [Style & Aesthetics]`.
- **Advanced (2–15 s clips):** `Subject + Scene + Motion + Aesthetic Control +
  Stylization`, with a rule matrix: motion carries **velocity, physics, amplitude**
  (never static states like "standing"); aesthetics carries framing size, angle, lens
  (never a defaulted stationary view); subject specific (clothing, textures); scene
  layered (foreground/background, weather, time of day).

## The I2V rule — the headline for the start-frame route

> "In I2V mode, do not waste tokens describing the static elements visible in the
> source picture. Only prompt the *subsequent action or transformation*."

Direct design input for any start-frame spec's prompt: **the frame carries the scene;
the prompt carries the performance and the camera.** UNTESTED here. It also names a
measurable question the record has not asked: whether scene re-description in an I2V
prompt interacts with the two observed world-behaviors (replacement vs persistence,
E10/E11 — each seen on one seed). A spec's question, not a claim.

## Camera anchoring — the document's claim vs this repo's measurement

The document: omitting camera directions "defaults the output to flat, stationary
framing." **E11 wave 1 measured the opposite on the 2.2 plain tier** — an uncommanded
push-in with no camera language present. The measurement is the record for our tiers;
the document's claim is recorded as its own. Both point at the same cheap probe already
on the shelf: one arm with an explicit static-camera clause.

## Multi-shot storyboards (version-unpinned in the document)

Shot-block syntax — `[Theme] + Shot [N] [start–end] + [action]`, with explicit
`Hard cut transition` / `Cross-dissolve transition` keywords opening new blocks. This
rhymes with consult #7's narration shelf (beats → camera → chaining →
area-scheduling). Which of our runnable models honor timeline blocks is a catalog
question for the consult channel before any spec leans on this syntax.

## Wan 2.6+ reference-video mode — flagged for the Director

`@Character` identity tags lock a pre-uploaded character reference or digital actor
into the generation (max two characters; quoted dialogue after a tag invokes lip-sync
and vocal generation). **This is a native mechanism aimed at exactly this repo's
product — one persistent main character** — and if ever considered it constitutes a
new conditioning tier: a consult-brief trigger by the standing list, plus full
licence/terms rows for the exact variant before the first credit. Knowledge, not
admission.

## The document's mistakes list (as stated, with our calibration)

- Kinetic motion verbs over passive descriptors ("bursting, cascading, sprinting") —
  prompt-side motion discipline. Calibration from the record: prompt-side treatment
  for hands at speed was measured insufficient twice (E11 w1, w3); this rule does not
  overturn that measurement.
- I2V over-description (the rule above).
- Ambiguous camera blocks (the claim above, held against our measurement).

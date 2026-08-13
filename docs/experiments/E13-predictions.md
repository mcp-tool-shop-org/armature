# E13 — the executor's predictions

**Written 2026-08-13 by the executor session, before any E13 generation existed** — and, as
it turned out, before any generation was submitted at all (the run halted; see
[E13-report.md](E13-report.md)). They are recorded anyway, because a future unpark of this
route deserves a prediction committed while its outcome was still unavailable.

## Blindness, stated exactly

**Blind with respect to every E13 artifact.** No E13 generation exists, none was submitted,
and no output of this route has been seen by this seat.

**Not blind with respect to the inputs.** When these were written I had already looked, at
full size, at: the A2 reference clip's frames (0/30/60/80), facet's `twin_front.png` /
`twin_back.png`, the `facet_E33/twins` material plates, and the `turn_final` / `turn_clay`
8-view turnarounds. That ordering is deliberate — the dispatch required every reference to be
looked at before upload — and it means these predictions are informed by the references and
blind only to the results. Where that matters most is P5, which is a prediction *about* a
defect I had already seen in the references; it is marked as such rather than passed off as
foresight.

**One expectation that preceded its measurement but was not committed in writing.** On
reading `upload_file`'s image-only allowlist and `LoadVideo`'s empty option list, I said
in-session that the clip slot looked unreachable *before* running the upload probe. That was
a spoken expectation, not a committed prediction, and it is recorded here as the weaker thing
it is.

## The predictions

The advisor's H-E13a–d were written blind at spec time and are not restated here. Mine differ
in one deliberate way: each conjunction is split, because a compound clause that comes out
half-right cannot be scored (CLAUDE.md — predict each clause of a conjunction separately).

| id | clause | prediction | reasoning |
|---|---|---|---|
| **P1** | A1 (stills): the generated figure reads as a **jointed wooden/clay mannequin** — the material and articulation class | **HOLDS on 2 of 2 seeds** | the reference stills are unambiguous about material and visible ball joints; material class is the easiest property for a reference-lock tier to carry |
| **P2** | A1: the figure's **proportions** hold — elongated limbs, small head relative to body, the long shin and thigh the mesh actually has | **FAILS on 2 of 2 seeds** | the tier is trained on human performers and the reference is a non-human proportion. This is the clause I expect to separate "identity locked" from "a mannequin-ish person" |
| **P3** | A1: the **face** reads as the mannequin's carved features (closed slit eyes, the fixed slight smile) rather than a rendered human face | **FAILS on at least 1 of 2 seeds** | a carved non-face is what a human-trained tier is least equipped to preserve, and the three-quarter and profile references are holed at exactly the face |
| **P4** | model-decided worlds **differ** across the two seeds within an arm | **DIFFER** | agrees with the advisor's H-E13c; the seed-volatility law, twice sighted |
| **P5** | the white texture-projection holes on the three-quarter/profile references propagate into output as light blotches, material discontinuities, or a bleached limb | **APPEAR on at least 1 of 2 seeds** | **not blind** — I had seen the holes before writing this. Recorded because it is the specific reason those plates should not be submitted as they stand |
| **P6** | `watermark=false` is honored — no visible watermark | **YES** | agrees with the advisor's H-E13d |

## What would separate the outcomes cheaply

P2 and P3 are the load-bearing pair. If both hold, the tier carries a non-human stylized
identity from stills alone — the result the composed route would be adopted on. If P1 holds
while P2 and P3 fail, the tier carries *material* but not *character*, which is a much weaker
product claim. Those two outcomes look similar on a contact sheet and separate at the
Director's zoom, which is where they belong.

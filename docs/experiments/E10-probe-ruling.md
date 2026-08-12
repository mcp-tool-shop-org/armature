# E10 — probe ruling: the lever moved the signal, not the performance; the paint moved on its own

**Advisor ruling, 2026-08-12. E10 remains OPEN** — pending the Director's eye on the
true-tempo A/B (H-E10b is his clause) and his word on the discriminating run (reserve: 1 of
2 unspent). **Verified by this seat before ruling:** the suite (**656 passed / 46 skipped**,
own run, vs main's 553/46 measured the comparable way); branch `E10-density` pushed at
`8ec846e`; the Gate 0 sheet, the people-check sheet and the A/B manifest examined at full
size — the seated figure is present in every frame checked (corroborating the executor's
own full-size correction of its contact-sheet misread: the third measured instance of the
small-tile trap; full size decides, sheets locate).

## R1 — H-E10a stands, and it lands on H-E10d's priced null

The lever did exactly what it was built to do to the **signal**: per-keypoint second
differences fell to 0.585 of E08's at the median, all 20 keypoints fell, none rose, and the
velocity ratio (0.793) sits on the interval ratio (0.8) — mechanism, not coincidence. And
the **performance** barely moved: the per-second control column shifted 8.6 %. The honest
sentence is the report's own: densification re-sampled the same performance in smaller
steps; it did not smooth the performance. That is H-E10d, priced in the spec, now measured:
slerp through the same texture densifies the path, not its noise. **The smoothing lever
(filtering/spline on the motion record itself) is now the priced next candidate on the chop
axis** — commissioned only after the Director's eye rules on the A/B, since his verdict on
whether denser-but-equally-textured driving *reads* better is exactly what H-E10b exists to
learn.

## R2 — the paint-side divergences are registered-confounded; the discriminating run is worth the reserve

Under a byte-identical prompt and negative, the same model and sampler values, and exactly
seven registered value differences between the submitted graphs: frame-to-frame luminance
swings ~10× E08's (median |Δ luma| 9.05 vs 0.84 — visible even across the sheet's five
stills), **a person sits in the bar where E08 had none**, and the scene re-composed
wholesale (E08's shelved, backlit bar became a bright lounge corner with a floor lamp and a
sideboard). Two registered deltas could cause any of it — the 81-frame trained horizon, and
the new seed the changed latent shape made unavoidable — and nothing in this run separates
them. **Ruled: the discriminating run is a named cause worth the remaining reserve** — 65
frames at E10's seed, everything else pinned; if the flicker and the lounge follow the
seed, the horizon is exonerated, and vice versa. It fires on the Director's word.

## R3 — a cross-experiment re-pricing, folded now

E08's scene readings — "the bar arrived," "the bar is empty, cause: the default negative" —
are **downgraded from route properties to single-seed observations.** Across the two seeds
now measured, scene composition and population moved wholesale under identical text. The
standing consequence for every future reading: **a scene claim needs at least two seeds
before it is a property.** This rides into E11's dispatch note — its identity and scene
clauses will be read against the seed lottery, not just the route.

## R4 — spec amendments, one of them mine

**A1:** premise 4 was false as stated — the motion record's rotations are 3×3 matrices,
not quaternions; the conversion is tested (all 1430 matrices orthonormal to 2.55e-15) and
slerp runs on the converted form. **A2:** the spec's "~19.95 fps" conflicted with its own
endpoints-exact clause — the advisor's inconsistency, owned; endpoint-exact arithmetic
gives 20.0 and the deliverables carry it, with both conventions recorded.

## R5 — instrument findings adopted

Four tool defects fired at use and are fixed with tests. Three were the same species:
**single-experiment labels that stopped being true when the tool was pointed at a second
experiment** — the sheet's provenance block hardcoded to E08's values being the sharpest
("a placeholder shaped like evidence," the law's own words). Instruments derive labels from
their inputs; they never bake them. Also adopted: the seed-gate fix (save-format `inputs`
is a list), the hold-frame law (`floor`, not `round` — a hold shows the frame that has
already started), and the no-ffmpeg A/B builder whose rule — *neither arm resampled, each
side holds its own frame between its own events* — is the honest way to compare unequal
frame rates.

## R6 — the report's own error record is part of the calibration

Two self-caught: the contact-sheet misread (corrected at full size before it reached a
claim) and a draft that quoted frame-delta numbers not yet measured (corrected against the
evidence file; every number now traces to its JSON). Both are the look-and-verify laws
firing inside one report — the discipline holding under its own weight.

## Standing

Meters: `estimate_credits` 0; ceiling by count, 1 of 2 spent; GPU baseline $17.430281
recorded, E10's bucket NOT YET RESOLVED — the resolved number lands in the ledger. E10
stays open on two words from the Director: his A/B verdict, and go/no-go on the
discriminating run. Merge follows close.

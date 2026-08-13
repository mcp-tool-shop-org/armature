# S04 — the executor's predictions, committed before the first measurement

**Committed on `S04-run` before any S04 measurement has been read.** Tasks A and B are
built and their suite is green at the previous commit; nothing rendered has been looked at.
The unit that follows is counted before it is predicted, and each clause of every
conjunction is predicted separately.

## Blindness, disclosed honestly

| what | blind? |
|---|---|
| the S04 spec, including the advisor's H-S04a / H-S04b / H-S04c | **NO** — read in full at dispatch, as instructed |
| the Task A / Task B implementation | **NO** — this session wrote it |
| every S04 measurement, calibration and Task-C alike | **YES** — none read at this commit |
| the S03 kit's parameters (elevation 0, 352x1024, radius 1.7282, GLB `9e20ea7d…`) | **NO** — read from its manifest while enumerating |

**One disclosure that is not tidy.** The calibration script was run once before this commit
and raised on a dangling camera datablock — a later `read_factory_settings` frees the
camera the readback wanted — *before* printing any measurement. Three PNGs were written to
`outputs/_test_ortho_convention/` in that run. **None was opened, measured, or displayed**,
and no number from the calibration has been seen. The predictions below are blind to it in
substance; they are not blind to the fact that Blender accepted `type='ORTHO'` far enough
to render three files without erroring, which is weak evidence for P-C1 and is stated
rather than hidden.

## The units

* A **view** is one rendered azimuth cell of the proof GLB
  (`E:\AI\training\facet_E33\out\performer_textured.glb`, sha256 re-verified this session as
  `9e20ea7d800c0ffd2cff101a5e1bcc01fa13c620bbbe3ef05ae23b093547b1aa`, 21,588,628 bytes) at
  elevation 30°, 1024x1024, RGBA. **8 views per set, two sets** — one ortho, one
  perspective sibling at the identical preset — so **16 cells** in Task C.
* A **calibration render** is one 352x1024 RGBA frame of a 0.4-unit cube centred at world
  (0, 0, 0.75), camera at azimuth 270° / elevation 0°. Three of them.
* **`height_frac`** is Gate WHOLE's reported `(y1 - y0) / 1024` of the *projected* cloud.
* **`delta_px`** is measured-minus-predicted per side, rendered alpha bbox minus projector
  extent.

## Calibration predictions

| id | clause | prediction |
|---|---|---|
| P-C1 | `cam_data.type` reads back `ORTHO` and `ortho_scale` reads back `2.0` | YES to both — high confidence, and see the disclosure above |
| P-C2a | the cube's measured raw bbox is **≈205 px wide** (`0.4 / (2.0·352/1024) · 352 = 204.8`) | 195–215 px |
| P-C2b | the transposed convention's **70.4 px** is NOT what the render shows | correct — the two differ by 2.9x, so this cannot come out ambiguous |
| P-C2c | the cube is **as tall as it is wide in pixels** (a square world span on square pixels), ≈205 px | 195–215 px |
| P-C3 | `Image.pixels` is **bottom-up**: a cube high in the world lands in the LAST rows of the raw array | raw `y0` ≈ 844 and `y1` ≈ 946; both > 512. If it is top-down instead, ≈77..179 |
| P-C4 | parallel projection — the bbox at radius 30 equals the bbox at radius 3 | identical within 1 px on all four sides |
| P-C5 | doubling `ortho_scale` to 4.0 halves the pixel size | ≈102 px span, 95–110 |

P-C3 is the one that matters most and the one with no fallback: it is the sole premise
carrying `_measure_alpha_plane`'s flip, and it was measured *because* nothing derived from a
centred figure's bbox can see it.

## Task-C predictions

| id | clause | prediction |
|---|---|---|
| P-T1 | 8/8 ortho views render, Gate ALPHA green on all 8 | YES — high confidence. Agrees with the advisor's H-S04a |
| P-T2 | Gate CROP silent on all 8 ortho views | YES — high confidence. Agrees with H-S04b, and for a reason the advisor's wording does not give: at `height_frac` 0.831 the vertical clearance is ≈86 px per side, and a 1024-wide frame holds a standing figure of maybe 300 px width with ≈350 px to spare laterally. The decimation gap would have to be enormous |
| P-T3a | `abs(delta_px) ≤ 10` on all four sides of all 8 ortho views | YES, but this is my least confident numeric clause — the decimated cloud keeps world-axis extremes, and a *screen* extreme at a 45° azimuth need not be one of them |
| P-T3b | the sign pattern is measured-wider (`Δx0 ≤ 0`, `Δx1 ≥ 0`) on at least 6 of 8 views | YES |
| P-T4 | the perspective sibling: Gate ALPHA green 8/8 **and** Gate WHOLE green 8/8 | YES to both — it is the path S03 already ran, at a new elevation and frame |
| P-T5 | across the 8 ortho views, exactly one sits at `height_frac` 0.831 and none exceeds it | YES — true by construction of the solve; this predicts the solve is wired to the render, not that the arithmetic is sound |
| P-T6 | **`min(height_frac)` is HIGHER across the ortho set than across the perspective set** | YES. This is the instrument's whole purpose stated as a falsifiable number: under perspective the near shoulder swings toward the lens and each view draws at its own scale, so the set spreads; under parallel projection nothing varies but the true silhouette. If this comes out equal or reversed, the ortho path is not delivering the property it exists for |
| P-T7 | wall-clock per view at 1024x1024 EEVEE on a 21 MB textured GLB | 5–30 s; wide, because I have not measured this rig at this size |

**H-S04c gets no prediction from this seat.** Whether the cells read as sprite cells at the
Director's eye is his verdict alone, per the E14 law the spec cites. A prediction from an
executor on a preference clause would be a seat grading a judgment that is not its own.

## What would make each of these a miss

P-C2 misses if the aspect convention is transposed — the discriminating ratio is 2.9x, so
there is no ambiguous outcome. P-C3 misses if the rows are top-down, in which case the flip
in `_measure_alpha_plane` is backwards and Gate CROP's border naming is wrong in every
report it will ever write; the fix is one slice and the miss is worth more than the hit.
P-T2 misses if Gate CROP fires, which is a **halt** — reported with its evidence, not
tuned past. P-T6 misses if parallel projection does not flatten the per-view scale spread,
which would mean the sheet does not have the property the shot-set is for; that is a
negative result and a full success.

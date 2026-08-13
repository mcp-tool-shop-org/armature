# S03 — predictions, committed before any output exists

Executor session, 2026-08-13, worktree `E:\AI\armature-S03`, branch `S03-run`.
Dispatch: [S03-performer-reference-kit.md](S03-performer-reference-kit.md).

**Blindness, stated per prediction.** Everything below is written before the render runs
and before any Task-C submission. Where a prediction is *not* blind — because the quantity
was already measured this session while resolving a premise — it says so and says what was
measured. A prediction dressed up as blind when the answer was already on the screen is
worth less than no prediction at all.

---

## What was measured BEFORE predicting (so the predictions below are honest about it)

These are premise resolutions, not results. They are recorded here because several
predictions lean on them and a reader is entitled to know which.

| measured | value |
|---|---|
| `turn_final` alpha extrema, all 8 views | **(255, 255)** — re-measured this session; the dispatch premise holds |
| `turn_final` size / figure rows | RGBA 352×1024; figure spans rows 86–937 on every view (0.831 of frame height) |
| `turn_final` figure columns | widest at views 0 and 4 (33–317), narrowest at 2 and 6 (106–245) |
| the A2 clip's start-frame GLB | `performer_dance_ema.glb` `cd4e2f6e…` — **all three** E12 start-frame provenance records name the same one |
| the lineage above it | `performer_textured.glb` `9e20ea7d…` → (rig_repair) → `performer_repaired.glb` `501a6db7…` → (rig_character) → `performer_auto.glb` `7f56c9ac…` → (lift_solve + motion) → `performer_dance_ema.glb` |
| `performer_textured.glb` in two places | byte-identical (`9e20ea7d…`) at `facet_E33\out\` and `armature-E07\outputs\E07\subject\`; E33's manifest names it `_deliverable` |
| the performer's world facing | `facing_y_sign: -1.0` (feet primary, head cross-check agrees) — front is azimuth 270° |

---

## Task A — the RGBA-true turnaround

**P-A1 · the canonical asset — NOT BLIND.** The unposed asset on the A2 lineage is
`performer_textured.glb`, and it is the same file `turn_final` was rendered from. Resolved
by hashing every link before this was written. Recorded as a prediction only so the report
can state plainly that it was settled by measurement rather than by picking from the
dispatch's premise list — **which does not name this GLB at all.** The dispatch's
"Performer GLBs on the rig" row lists `performer_300k`, `performer_raw` and
`performer_dance_ema`; choosing from that list alone yields an untextured or a posed
subject, and the coherence row fails.

**P-A2 · alpha — BLIND.** All 8 views come back with `alpha_min = 0` and
`alpha_max = 255`. Reasoning: `film_transparent = True` with `color_mode = "RGBA"` and no
floor plane, so the world void is genuinely unwritten and the mannequin is opaque
geometry. **Gate ALPHA passes on all 8.** If any view returns (255, 255) that view FAILS
and is reported, not shipped.

**P-A3 · the holes persist — BLIND.** The white unpainted patches E13 recorded stay
exactly where they were: present on views 1, 2, 3, 5, 6, 7; views 0 and 4 largely clean
with small white nicks at the hands. Re-rendering cannot repaint a texture atlas, and the
atlas is the same file. **A new render that fixed the holes would falsify my model of what
the defect is**, and would mean the holes were a render artifact rather than a projection
gap — which is the more interesting result and the one I am not expecting.

**P-A4 · transparency ordering — BLIND.** Views 2 and 6 (the profiles) carry the
*highest* transparent fraction; views 0 and 4 (front and back) the *lowest*. A profile
presents less silhouette to the camera than a front view of the same figure. Predicted as
an ordering rather than a magnitude because I have no calibrated figure for how much of a
352×1024 frame a mannequin's silhouette fills.

**P-A5 · magnitude, separately — BLIND, low confidence.** Every view's transparent
fraction lands in **0.70–0.90**. Stated as its own clause rather than folded into P-A4,
because an ordering and a magnitude are two predictions and a conjunction hides which one
was wrong. This is the weakest prediction on the page.

**P-A6 · Gate WHOLE — BLIND.** Passes on all 8. The radius is solved on the tallest
projected view, and the old set's widest view spans 81% of frame width, so there is room.
The risk I am accepting: the lens is a recorded choice (50 mm, the repo's standing value)
and facet's lens for `turn_final` is not recorded anywhere on this rig. A wider effective
field could push the arms past the border at three-quarter, and Gate WHOLE is exactly the
check that would catch it.

**P-A7 · Gate TURN — BLIND.** All 8 views byte-distinct.

**P-A8 · the coherence row — BLIND as to the look, though the lineage is measured.** The
rendered figure is the same wooden/clay jointed lay-figure mannequin that dances in the A2
clip, in the same rest pose as `turn_final` (arms at sides). Verified by eye at full size
in the report, not asserted from the hash chain.

---

## Task C — the frames→VIDEO chain

**P-C1 · the frame pin — BLIND.** All 81 lossless frames re-hash to the E12 `gate_b`
record, n = 81 exactly.

**P-C2 · credits — BLIND.** `estimate_credits` returns **0 partner credits** for the
assembly graph, metered as GPU-hour. Reasoning: `CreateVideo` carries `api_node: false`,
and no partner node is in the graph by construction. **Any partner-credit estimate above 0
halts the run** — this prediction is the one whose failure stops everything.

**P-C3 · the batch link — BLIND.** The E02 batch mechanism carries all 81 frames into
`CreateVideo`'s `images` socket. Recorded as ASSUMED in the dispatch's own premise table;
this is the first time it is exercised at 81.

**P-C4 · the decode-compare — BLIND, and split into two clauses.**
 - **frame count and rate:** the produced VIDEO decodes to 81 frames at fps 16.
 - **pixels:** the decoded frames are *not* bit-exact against the source PNGs. The save
   class encodes, and an encoder that subsamples chroma changes true-RGB content while
   leaving it visually identical — the precise disease `GateRRoundTrip` was written for
   (`-qp 0` is luma-lossless while x264 still defaults to `yuv420p`). I expect a small
   non-zero per-frame difference, and I expect it to be *structured* (largest at colour
   edges) rather than uniform.

Predicted separately because the count clause and the pixel clause can fail independently
and a conjunction would hide which.

**P-C5 · the residual — NOT A PREDICTION.** Whether the r2v node accepts a constructed
VIDEO at runtime is **not provable at zero credits**, is not predicted here, and stays
**ASSUMED** in the report in those words.

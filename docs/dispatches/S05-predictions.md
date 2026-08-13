# S05 — the executor's predictions, registered before the first Task-B render

**Committed before any Blender run of this session.** No S05 artifact exists at the time
of writing: no render, no manifest, no sheet. Task A is built and its suite is green
(1261 passed, 48 skipped, identical under `-O`), and Task A is build-and-test — the judged
artifacts are Task B's.

## Blindness, disclosed

**Not blind to:** the S05 spec and its four hypotheses; the S04 report in full, including
its per-view measurement table, its solved scale, and its per-view clearances; the S04
ruling; the source of `render_turnaround`, `turnaround`, `framing`, `startframe` and
`make_shotset_sheet`, including the Task A code this seat wrote today.

**Blind to:** every S05 measurement. Nothing has been rendered.

Most of what follows is arithmetic on S04's published numbers rather than intuition, and
that is stated per prediction so the scoring can tell a derivation from a guess.

## The identity every prediction below rests on

Under parallel projection a point's pixel offset from the projected frame centre goes as
`1 / ortho_scale`, with no distance term (`framing.project`, the ortho branch; pinned by
`test_screen_size_scales_as_one_over_the_pin`). So pinning at `k × solved` multiplies every
projected offset by `1 / k` about the frame centre. `k = 1.25` shrinks by 0.8; `k = 0.80`
grows by 1.25.

## E-1 · Arm SOLVED — no pin

| id | clause | prediction | basis |
|---|---|---|---|
| P-1a | the solved scale is **bit-identical** to S04's `1.1235359256161628` | HIT | same GLB, same preset, deterministic import → deterministic `framing_cloud` → deterministic bisection; the solve path is untouched by Task A |
| P-1b | Gate ALPHA 8/8, Gate TURN 8 distinct, Gate WHOLE 8/8, Gate CROP silent 8/8 | HIT | S04 measured exactly this on this GLB at this preset |
| P-1c | the manifest records `ortho_scale_source: "solved"`, `ortho_scale_pinned_as: null`, and a solve record naming `height_frac` 0.831 | HIT | Task A, keyed off the source |
| P-1d | per-view rendered `px h` reproduces S04's column exactly: 829, 855, 849, 834, 829, 841, 849, 841 | HIT on all eight | same render, same threshold; the alpha bbox is robust to sub-sample noise. Deliberately a conjunction of eight, scored per view |
| P-1e | tightest clearance 62 px, on view 1 | HIT | S04's per-view clearances |
| P-1f | wall-clock 5–10 s for the 8-view run | HIT | S04 measured 7.03 s; P-T7 already missed by predicting per-view seconds, so this one is stated on the S04 measurement and not on a prior |

## E-2 · Arm PINNED-ROOMY — pin = 1.25 × solved

The pin is typed at full precision from arm 1's manifest. `1.25 × 1.1235359256161628`
is exactly representable as `1.4044199070202035`.

| id | clause | prediction | basis |
|---|---|---|---|
| P-2a | Gate ALPHA 8/8, Gate WHOLE 8/8, Gate CROP silent 8/8 | HIT | every offset shrinks by 0.8; nothing can reach a border it already cleared by 62 px |
| P-2b | the largest view's rendered `px h` lands at **684 ± 3** (855 × 0.8) | HIT | the 1/k identity. The spec's H-S05b allows ±12; this seat predicts the tighter band, since the only slack is sub-pixel threshold behaviour at the silhouette edge |
| P-2c | every view's `px h` = its S04 value × 0.8, each within ±3: 663, 684, 679, 667, 663, 673, 679, 673 | HIT on all eight | same identity, scored per view |
| P-2d | the rendered silhouettes move **toward** frame centre; mean centre row ≈ **526** (S04's 529.4 pulled to 511.5 + 17.9×0.8) | HIT | the scaling is about the frame centre, not about the figure |
| P-2e | every view's minimum clearance is **> 140 px** | HIT | view 1's bottom clearance, the tightest in S04 at 62 px, becomes ≈152 px |
| P-2f | the manifest records `ortho_scale_source: "pinned"`, `given_text` exactly as typed, `ortho_scale_solved_for: null`, and no `height_frac` value anywhere in the pinned block | HIT on all four | Task A, red-tested |

## E-3 · Arm PINNED-TIGHT — pin = 0.80 × solved

`0.80 × 1.1235359256161628 = 0.8988287404929302`.

**This seat's prediction differs from the spec's H-S05c, and the difference is the point of
registering it.** H-S05c predicts Gate CROP raises on view 0. This seat predicts **Gate
WHOLE raises on view 0 first, and Gate CROP is never reached.**

The reasoning, entirely on S04's published numbers and the code:

1. Gate WHOLE reads the **projected decimated cloud**; Gate CROP reads the **rendered
   alpha**. In the render loop `gate_WHOLE` is evaluated inside the `rec` dict literal and
   `gate_view_crop` is called after `rec` is assigned, so WHOLE is strictly upstream.
2. On a **solved** run Gate WHOLE cannot fail on the height axis — the solve fits that same
   projection to `height_frac ≤ 0.831` by construction. That is S04's "Gate WHOLE passes by
   construction", and it is why S04 could describe CROP as the andon on the direction the
   solve does not bound.
3. A **pin is not fitted to anything**, so it re-opens that direction. S04's view 0 projected
   at `height_frac` 0.8094; at 1.25× that is **1.0118 — taller than the frame itself**. A
   silhouette taller than 1024 rows cannot clear both borders by `MARGIN_PX = 2.0`
   regardless of where it sits, so Gate WHOLE raising on view 0 is arithmetic, not a guess.
4. The gap CROP alone can see is the **decimation gap** between the projected cloud and the
   rendered silhouette — S04 measured that at ≤ 7.93 px against clearances of 62–86 px. The
   band of pins where CROP fires and WHOLE does not is therefore roughly 1–2 % wide. A
   0.80× pin is 25 % in, far outside it.

| id | clause | prediction | basis |
|---|---|---|---|
| P-3a | an andon raises on **view 0** (az 270) and the run halts there | HIT | the first view rendered is the first one measured |
| P-3b | the andon that raises is **Gate WHOLE**, not Gate CROP | HIT — and this contradicts H-S05c | clauses 1–4 above |
| P-3c | it raises on the **bottom** border, not the top | HIT | the ortho silhouette sits low (S04: rendered centre 522.5 against a frame centre of 511.5), so growth about the centre crosses the bottom first |
| P-3d | the bottom margin is **−15 to −26 px**, and the top margin stays positive (≈ +7) | HIT both clauses | projected extent ≈ 108.4..937.2 scaled by 1.25 about 512.0 → ≈ 7.5..1043.5 |
| P-3e | Gate ALPHA **passes** on that view before WHOLE raises | HIT | a cropped figure has transparent pixels and opaque ones; this is the clause that makes the raise informative rather than an empty frame |
| P-3f | partial output is **exactly one PNG** (`tight_0.png`) and **no manifest** | HIT | the file is written before the gate is measured, and the manifest is written after every view |
| P-3g | `RENDER_TURNAROUND_OK` does **not** appear in the arm's stdout | HIT | the contract line is printed last |

Whichever andon fires, the raise is this arm's recorded result. Nothing will be retried, no
pin adjusted, no sweep continued. **What a WHOLE-rather-than-CROP raise means for the
spec's design is the advisor's to rule; this seat reports which gate fired and its
evidence.**

## E-4 · The sheet

| id | clause | prediction | basis |
|---|---|---|---|
| P-4a | the compare sheet's two rows tag as `SOLVED` and `PINNED`, read off each manifest | HIT | Task A, tested |
| P-4b | both rows' figures sit at the **same cell size**, the pinned row's figure smaller in an identically-sized frame | HIT | the cells are pasted 1:1 and never resampled; only the figure changes |

## H-S05d

The spec's fourth hypothesis is the Director's clause explicitly. **This seat gives it no
verdict**, per the E14 law the spec cites. The cells go to his eye.

## What would falsify the whole shape

If arm SOLVED does not reproduce `1.1235359256161628` bit-for-bit, then something between
S04's run and this one is not deterministic, and every number in E-2 and E-3 — all of which
are derived from S04's table — is quoted against a floor nobody has measured. That is the
first thing to read in the report.

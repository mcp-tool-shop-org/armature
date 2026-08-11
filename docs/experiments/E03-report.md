# E03 — report: does the control sequence govern authored motion?

**Seat:** executor · **Written:** 2026-08-10, after the runs · Spec:
[E03-authored-motion.md](E03-authored-motion.md) (with Amendment 1) · Predictions:
[E03-predictions.md](E03-predictions.md), committed `44c0641` at
`2026-08-10T20:18:48-04:00`, **before any submission**.

**Three generations submitted, 12 credits projected against a ceiling of 4 generations. The
fourth was not spent.** No gate fired.

---

## 1. Predictions, and whether they were blind

**Blind to** all three generations: nothing had been submitted when
[E03-predictions.md](E03-predictions.md) was committed, and its timestamp is git's.

**NOT blind to** three things, each disclosed in that file before the fact:

1. **The control sequences** — I rendered them and had read their manifests.
2. **The instrument's calibration.** `measure_arm.py` was run against the *control* frames
   and checked against the control's own authored ground truth before the predictions were
   written. That is why a tolerance could be stated at all. It involved no generated output.
3. **E02's results**, including its closing ruling.

## 2. ⚠ The spec's readout could not be measured, and what replaced it

The spec asks for **"the frame index at which it passes horizontal"** while specifying the
motion as **"from T-pose to overhead."** A T-pose arm *starts* horizontal, so it never
passes horizontal — the answer is frame 0 for every possible outcome, and the arm cannot
move it. That is the one property this repo forbids a readout to have.

Replaced **before anything was rendered and before the prediction existed** with the
**midpoint (45°) crossing**: monotonic, crossed once, unambiguous by eye, authored rather
than measured. **Authored crossing: frame 16.000**, exactly, from
`(45 − 0) / 90 × 32`. Flagged for the advisor to overrule — it changes how a registered
prediction is read.

## 3. The subject, and the three defects found building it

`tools/make_test_armature.py --pose-arc=arm_r_raise`, thickness 0.030, 33 frames at 16 fps,
0° → 90°. Licence-clean by construction: authored geometry, nothing acquired, no row in
`docs/license-map.md` required.

**The spec says only the generator needs changing. It was short by one tool.**
`configure_render` pinned `scene.frame_end = 1` — E01's deliberate choice so that only the
camera could move — so an animated GLB would have rendered 33 identical frames with nothing
reporting it.

Three defects were found before any credit was spent, all mine:

| # | defect | how it was caught |
|---|---|---|
| 1 | **The rest-transform clobber.** `add_limb` aims each cylinder via the *object's* `rotation_quaternion`; `join` hands that to the joined group; assigning `rotation_euler` for the arc discarded it. The arm stood upright before the performance began and the arc ran vertical → backwards-horizontal, while every F-curve read exactly 0°, −45°, −90° as authored. | `check_pose_arc_roundtrip.py`, against the authored ground truth |
| 2 | **The fps ordering.** glTF stores key times in **seconds**. `prepare()` imported the GLB *before* `configure_render` set the rate, so a 33-key action authored at 16 fps landed on frames 1–49 at Blender's default 24. The render sampled 1–33 and captured **two thirds of the arc**: a 0–90° raise arrived as 0–60°. | the union bbox topped out at 1.1013 m where the wrist reaches 1.1314 m — sin(60°)/sin(90°) to five digits |
| 3 | **Two arms differing in more than one thing.** B1 fits the camera to the union of all frames and normalises depth over its own extent; B3 does both from the bind pose. Measured, B1 frame 0 and B3 held identical geometry and still differed by up to **26 of 255 levels**, at a different scale. | direct pixel comparison |

**Defect 2 is the one worth carrying forward: G6 PASSED on it.** 33 distinct geometry
signatures, because the subject genuinely moved — just not through the authored arc. **G6 is
necessary and not sufficient**; only the authored ground truth caught it. The andon now
lives inside `import_glb`, where the mistake is still cheap.

After fixing 3, **B1's frame 0 is byte-identical to B3's frames** — confirmed independently
by the content-addressed upload store, which returned the *same server name* for both.

## 4. Gate 0 — the sheets exist, and no arm metric is quoted above this line

| sheet | what it holds |
|---|---|
| `outputs/E03/sheets/E03-B1-gate0.png` | control \| output \| reference \| provenance, B1 |
| `outputs/E03/sheets/E03-B2-gate0.png` | same, B2 (control row labelled as not supplied to this arm) |
| `outputs/E03/sheets/E03-B3-gate0.png` | same, B3 |
| **`outputs/E03/sheets/E03-discriminator.png`** | **one control row, three output rows, same five frame indices — the panel the experiment exists to produce** |

Review clips at **0.5× (8 fps), built from `lossless/`, never from re-encoded video**:
`outputs/E03/review/{B1,B2,B3}_0.5x_8fps.mp4` plus `control_animated_0.5x_8fps.mp4`.

**No reference image anywhere.** Held constant (absent) across all three arms. Measured
legal, not assumed: `get_node WanVaceToVideo` reports `reference_image` as
`required: false`. The subject carries no identity for a reference to preserve, so supplying
a plate would have injected one the experiment is not asking about. The sheets label the
column as deliberately absent rather than filling it with a stand-in.

## 5. The instrument, and its error on a signal with known truth

`measure_arm.py`, estimator-free: classify subject vs background, take the pixels in an
annulus about the projected shoulder, report the angular lobe. **A diagnostic; it gates
nothing.**

| on the CONTROL, whose per-frame joint positions are authored | |
|---|---|
| authored crossing frame | **16.000** |
| **measured** crossing frame | **16.323** |
| **instrument error** | **0.32 frames** |
| bias, frames 0–28 | −0.9° ± 0.05, near-constant |
| bias at frame 32 (arm vertical) | −5.7° — the annulus keeps only the arm's hemisphere, so a vertical arm is clipped |
| subject fraction | 0.0496–0.0498, stable |

## 6. P1 — measured beside the prediction

**Clause A — does B1's figure raise an arm from horizontal to overhead?**

| | registered | measured |
|---|---|---|
| arm rises | **YES** | **YES** — angle sweeps **−1.4° → 83.6°**, span **85.0°**, monotonic |

**Clause B — the tolerance, registered before measuring: ±3 frames.**

| | frame |
|---|---|
| authored crossing | **16.000** |
| the control's own crossing, measured by the same instrument | 16.323 |
| **B1's crossing, measured** | **16.800** |
| **difference from authored** | **0.80 frames** |
| registered tolerance | **±3 frames** |
| point estimate registered | frame 18 |

**0.80 frames is inside the registered ±3.** Per-frame, B1 against the authored image angle:

```
frame     0     4     8    12    16    20    24    28    32
authored 0.00 11.25 22.49 33.71 44.92 56.13 67.34 78.55 89.78
B1      -1.40  9.76 20.51 31.59 42.64 53.95 65.74 76.82 83.56
```

**Clause C stays SUSPENDED**, as registered. No arm is ranked against another on a
magnitude.

**Amendment 1's halt condition does not fire, and here is why.** The amendment says a result
hinging on a small numeric gap is a halt. E03's result does not hinge on one: the separation
is **B1's 85.0° sweep against B3's 0.062°**, a factor of ~1370. The 0.80-frame timing figure
is reported as a number inside a pre-registered tolerance, and no conclusion rests on it.

## 7. P2 — the discriminator

**Clause A — does B3, under a control that holds still, raise an arm?**

| | registered | measured |
|---|---|---|
| B3's arm rises | **NO** | **NO** — angle constant at **−0.62° to −0.56°**, span **0.062°** across all 33 frames; the 45° readout is **never crossed** |

**Clause B — does B3 show any motion at all?**

| | registered | measured |
|---|---|---|
| some residual motion | **YES** | **YES** — temporal energy mean **0.177**, against a control whose own energy is **exactly 0.000** (33 identical frames) |

Estimator-free temporal energy, `mean |frame(t) − frame(t−1)|` over 32 transitions:

| series | mean | max | min |
|---|---|---|---|
| CONTROL animated (B1's input) | 0.3384 | 0.3675 | 0.3003 |
| CONTROL static (B3's input) | **0.0000** | 0.0000 | 0.0000 |
| OUTPUT B1 | 0.4365 | 0.5709 | 0.3396 |
| OUTPUT B2 | 0.2354 | 0.5115 | 0.1799 |
| OUTPUT B3 | 0.1773 | 0.3623 | 0.0906 |

**⚠ E02's timing-correlation diagnostic does not discriminate here, and the reason is a
property of this control, not of the arms.** Correlating each output's energy profile
against the animated control's gives B1 −0.440, B2 −0.299, B3 −0.108 — no separation. The
animated control's own profile is nearly **flat** (0.300–0.368) because the arm moves at a
constant angular rate, so there is almost no variation to correlate against and the
coefficient is dominated by noise. In E02 the control was an orbit, whose profile varies
strongly. **The numbers are reported so the failure is legible; nothing is read off them.**

## 8. P3 — what the model did with a shape that is not a person

| | registered | observed |
|---|---|---|
| B1 keeps the wire-armature look | **NO — I predicted a solid, person-like figure with limbs, a face, implied clothing** | **It kept it.** B1 renders a black wire figure of rods and balls on a plain grey field, matching the control's structure |

**This is a miss, and it is the clearest one in the experiment.** My reasoning was that the
prompt's "a single figure" plus the model's human prior would dominate a non-human control.
It did not.

**B2 is what makes the miss legible.** With no control at all, the same prompt and the same
seed produced **a photorealistic standing person** — not a wire figure, not a stick figure.
So the human prior is present and strong in this prompt; under B1 and B3 the control
overrode it. Subject fraction supports the eye read: control 0.0496, B1 0.0538, B3 0.0528,
**B2 0.4561**.

**Not an identity result.** This subject carries none.

## 9. B2's angle measurement FAILED, and is reported as failed

`measure_arm.py` returned an angle series for B2 (constant ≈ −67°) and **it is not
reported as a measurement.** Its subject fraction is **0.456** — 45.6% of the frame
classified as subject, against 0.050–0.054 for every other series. The modal-background
classifier is counting B2's lit background gradient as subject, which is exactly the
confound E02 caught and dropped its own coverage instrument over.

**The number is discarded, not quoted.** B2's answer comes from the panel and the clip: a
standing person, arms at their sides, no arm raise.

## 10. Every gate, with a verdict

| gate | verdict |
|---|---|
| **Gate L** — frame legality (480×832, 4n+1) | **PASS**, both control renders and all three payloads |
| **G2** — completeness | **PASS**, both control renders |
| **G4** — bbox sanity | **PASS**, max delta **1 px** against a 2 px tolerance, both renders |
| **G6** — subject motion (new) | **PASS** on the animated control (33/33 distinct signatures); **N/A** on the static control, where a constant subject is correct |
| **Gate B** — batch intact | **PASS (33 of 33)** on B1 and B3; **N/A** for B2, which has no batch |
| **Gate R** — round trip | **N/A for this route** — no codec in the path; retained with its 18 tests |
| **Gate C** — credit bound | **3 generations submitted.** Projected **12 credits** at E02's measured 4/generation, against a 4-generation ceiling. **The fourth was not spent.** The actual figure is **NOT OBSERVABLE** through any programmatic surface — E02 measured that `estimate_credits` returns 0 for open weights and the invoice lags with no bucket for the day. 12 is a projection, not a measurement; the Director's balance read is the instrument. |
| **Gate 0** — the sheet before the metric | **BUILT** for all three arms, plus the discriminator panel |

**Bridge fidelity**, re-measured on this experiment: `out = max(src − 1, 0)`, 33 of 33
frames, distinct signed deltas `{−1, 0}`, never `+1`. Reproduces E02 exactly.

## 11. Provenance

| | |
|---|---|
| model | `wan2.1_vace_14B_fp16.safetensors` · `umt5_xxl_fp16.safetensors` · `wan_2.1_vae.safetensors` |
| sampler | `uni_pc` / `simple` / 30 steps / cfg 6 / `strength` 1.0 |
| seed | `654654950714624`, identical across all three arms |
| frame | 480×832 × 33 @ 16 fps |
| B1 | `a72bf683-d2f2-42b1-90ae-a82b9b05e5fc` · payload sha256 `c9534db68c142c2f…` |
| B2 | `9e7a54e4-0f9c-4853-b388-911f7e4c2c70` · payload sha256 `56b1f2fec824af22…` |
| B3 | `8796261a-b549-4204-8b0f-838cce31f644` · payload sha256 `045a285a463e7bd4…` |
| control (B1) | `outputs/E03/control_posearc/depth_pershot`, 33 distinct images |
| control (B3) | `outputs/E03/control_static/depth_pershot`, **1** distinct image ×33 |
| depth window | **PINNED** `[3.181118, 3.363516]` on both, so the two arms share one tonal scale |
| camera | **PINNED** target `[0.000724, 0.0, 0.564974]`, radius `3.2893308729746606`, azimuth 270°, sweep **0°** — static |

**E02 was not moved by this work.** `tests/test_build_payload.py` pins A1a's and A2's
submitted payload sha256; both reproduce exactly after the refactor that added E03's arms.

**197 tests pass, including under `PYTHONOPTIMIZE=1`.**

## 12. Executor choices the spec did not arm — flagged for overrule

1. **The readout** — midpoint crossing instead of "passes horizontal" (§2).
2. **The prompt names no motion**, where E02's said "turns slowly on the spot". A prompt
   asking for the motion would hand B2 and B3 a reason to produce it, and the discriminator
   would be measuring the prompt.
3. **The negative drops "still image, static"** from E02's. Keeping it would pay the model
   to move under B3 — the exact arm whose job is to show what happens when the control does
   not move.
4. **No reference image**, held absent across all three arms (§4).
5. **The camera at azimuth 270°, sweep 0°.** The wire figure is planar at y=0 and the arc
   rotates about +Y, so a camera on the Y axis sees the whole performance face-on with no
   foreshortening. At azimuth 0 the arm would swing directly at the lens.
6. **The camera target, radius and depth window pinned numerically** rather than derived, so
   B1 and B3 differ in exactly one thing (§3, defect 3).

## 13. What this report does not claim

- No arm is ranked against another on any magnitude.
- Nothing here is an identity result; the subject has none.
- Nothing here is a judgement of whether any output is good. **The Director judges the
  sheets**, at full size and at 0.5×.
- The question of *how much* the model may add on top of authored motion is untouched.

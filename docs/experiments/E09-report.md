# E09 — report: the clean chain, calibrated to the point where it stopped

**Seat:** executor · **Run:** 2026-08-11 · **Worktree** `E:\AI\armature-E09`, branch
`E09-run` · **Spec:** [E09-clean-chain-calibration.md](E09-clean-chain-calibration.md) ·
**Predictions registered before the work:** [E09-predictions.md](E09-predictions.md),
commit `e7b4db5`, ahead of every artifact below.

**Credits spent: 0 of the ceiling of 8. Nothing was submitted to Comfy Cloud by this seat.**
Stage A and Stage B1 ran in full. **Stage B2 halted before its first submission on a gate
that fired with evidence.** Measurements only below; no judgement words, and no verdict on
whether any of it is good — that is the Director's at the sheets.

---

## 1. The two meters

| meter | reading |
|---|---|
| **Credits** | **0.** No `submit_workflow`, `run_template` or `run_saved_workflow` call was made. Every Comfy Cloud call this session was read-only: `list_saved_workflows`, `get_saved_workflow`, `search_templates`, `get_template`, `get_template_schema`, `get_usage_report`, `get_queue`. Account queue read `{running: 0, pending: 0}` at halt; no `prompt_id` exists on disk or in this transcript. |
| **GPU-hours (cloud)** | **0 attributable to this seat** — no cloud job ran. The workspace invoice line for 2026-08-11 reads $3.636 of *GPU Hours Product* for the whole account across all sessions; none of it is this seat's, and it is quoted only so the number is not mistaken for zero account-wide. |
| **GPU (local)** | Four headless Blender passes on the RTX 5090: the walk authoring, and three 65-frame render passes (source 1080p, the empty plate, the lifted 1080p). Wall clock is in each provenance sidecar's `elapsed_s`. The VRAM watchdog was verified alive before the first one and reported `kill@ VRAM 31200 MiB / RAM 90% / temp 87C`. |

## 2. Gate states

| gate | stage | state |
|---|---|---|
| watchdog liveness | before any GPU work | **PASS** — restarted and confirmed alive at session start |
| licence pin | throughout | **PASS** — no new dependency entered. MediaPipe's row (2026-08-11, Apache-2.0 at all three layers) already covers the `.task` model file; versions pinned in §3 |
| Stage A round-trip (`SOLVE`) | A | **PASS** — armed at 1e-9 of the character's own bbox diagonal, exercised by 30 tests including one that breaks a good solve on purpose and three that re-run that break under `-O` and `PYTHONOPTIMIZE=1` |
| fps ordering | B1 | **PASS** on every Blender invocation |
| framing | B1 | **PASS** — union inside frame, `union_x [0.286, 0.693]`, `union_y [0.170, 0.870]` |
| frame count | B1 | **PASS** — 65 PNGs for 65 authored frames, twice |
| coverage | B1 | **PASS** — min 0.0240 of the frame differs from the empty plate, at frame 0 |
| **detection** | **B1** | **PASS — a pose on 65 of 65 frames** |
| Gate N (pre/post), OBJ, SPACE, MOTION_RECORD, ARRIVED | B1 applier | **PASS** — all five, on the re-imported export |
| **Gate ROUTE** | **B2** | **FIRED — the halt.** §6 |
| **Gate C** (credit ceiling 8) | B2 | **ARMED, never tested** — ledger 0 of 8, because nothing was submitted |
| **Gate S** (seeds pre-registered) | B2 | **COULD NOT BE ARMED** on the only served route — §6. No seed list was committed, so there is no Gate S surface to unwind |
| **Gate L** (frame legality) | B2 | **PASS standalone, on the shape the spec asks for**: 832×480×65 is legal for Wan (832/16 = 52, 480/16 = 30, 65 = 4·16+1, ≤ 81). The served graph's own latent is 640×640×81, which is also legal but is not the requested shape |
| **lossless tap** | B2 | **NOT YET RUN** — it belongs to a generation that did not happen |
| Blender success-sentinel | A, B1 | **PASS** — every invocation ended on its `*_OK` line; a crashed `blender -b -P` exits 0, so the sentinel is the contract |

---

## 3. Environment, pinned

`E:\AI\armature\.venv` — Python **3.14.5**, `mediapipe` **1.0.0**, `numpy` **2.5.2**,
`pillow` **12.3.0**, `pytest` 9.1.1. `trellis2-env` was not touched.

Detector model: **`pose_landmarker_heavy.task`**, fetched from the **versioned** asset path
`.../pose_landmarker_heavy/float16/**1**/pose_landmarker_heavy.task` rather than
`latest/`, 30,664,242 bytes, sha256
`64437af838a65d18e5ba7a0d39b465540069bc8aae8308de3e318aad31fcbc7b`. Run in `VIDEO` mode,
`num_poses=1`, detection/presence/tracking confidences all 0.5, all recorded in the
measurement record. Heavy was chosen over Lite/Full deliberately: it is the most accurate
variant the licence row covers, so a negative result on it is the stronger one.

Blender 5.2 headless via PowerShell throughout.

### Premises, re-checked

| # | premise | outcome |
|---|---|---|
| 1 | performer GLB sha256 `7f56c9ac…2a24` | **CONFIRMED** — re-hashed this session, exact match. Copied into this worktree; the E07 tree was not written to |
| 2 | banked walk tooling at `E08-run` @ `8399d5a` | **CONFIRMED IN SUBSTANCE, CORRECTED IN PATH.** The commit and branch are right. The spec's checkout command names `tools/walk.py`, which does not exist at that commit and never did; the banked gait module is `tools/armature_core/walk.py`, with `tools/author_walk.py`, `tools/preview_walk.py` and `tests/test_walk.py` beside it. All four were taken, tests included |
| 3 | MediaPipe licence | **CONFIRMED** — versions pinned above; no re-fetch triggered because no version moved |
| 4 | a 33→22 mapping is definable without finger bones | **CONFIRMED** — the table is `SITE_FROM_LANDMARK` + `UNUSED_LANDMARKS` + `MODEL` in `armature_core/lift_solve.py`, as data. 19 of the 33 are read; the other 14 are listed with a reason each |
| 5 | 4 credits/generation | **NOT EXERCISED** — nothing was generated |
| 6 | the E02 A2 no-control payload shape serves the T2V clip | **FALSIFIED.** §6 |
| 7 | world landmarks are hip-origin, depth non-metric | **CONFIRMED BY MEASUREMENT, and it has a consequence bigger than expected** — §5.6 |

---

## 4. Stage A — the solver against mathematics

`tools/armature_core/lift_solve.py` (pure — no bpy, no numpy), `tools/lift_solve.py` (the
Blender applier), `tests/test_lift_solve.py` (30 tests, riding the same commit). Full suite
after the commit: **388 passed, 35 skipped**; with the later route gate, **404 passed**.

### 4.1 What the round trip closes to

| claim | measured |
|---|---|
| position round-trip, limb motion, observation from the rig's own kinematics inside the model | **< 1e-9 of the bbox diagonal** — gate armed and passing |
| the same under a whole-body rotation on `hips` | **< 1e-9** |
| authored rotations recovered, limb motion about the declared lateral hinge | **< 1e-9 rad** on every bone whose DOFs the landmarks determine |
| the solve is idempotent — `solve(FK(solve(x))) == solve(x)` | **< 1e-9 rad**, root drift < 1e-9 |
| torso twist, where `chest_base` is unobserved | **a projection, not an inversion** — residual bounded by the chest's own segment length, with `hip_L`/`hip_R` still exact to < 1e-9 |

**H1 was NOT blind and is disclosed as such** — the construction is exact by design. It is
also the clause where the predictions earned their keep, because "a miss is a bug" turned
out to be literally true twice.

### 4.2 Two defects the tests caught, and one claim that was wrong

1. **The hips' root was double-counted.** `solve_frame` returned the total offset while
   `fk_sites` treats that field as the translation *channel* and adds the pivot term
   itself. Every site landed 0.0036 out under any `hips` rotation — and a hips-identity
   motion round-tripped perfectly, so the bug was invisible whenever the root did not
   rotate. Fixed; the fix and the number are recorded at the code.
2. **A hinge was matched as a ray when it is a line.** Two elbows bending in opposite
   directions about the same lateral hinge forced a 180° twist onto one shoulder —
   **178.9° of error on a bone whose authored motion was a clean swing**, with its
   positions round-tripping perfectly throughout. θ is determined only modulo π; the
   minimal-twist branch is now taken and the assumption is written down.
3. **A claim, not code:** the first version of the module implied a parent's twist is
   *measured* when the bone has a child. It is not — the child can absorb any parent twist,
   so every twist angle explains the same landmarks. It is recovered only under an added
   anatomical constraint (the child bends about a hinge axis carried from the bind pose),
   and the module now says so. `twist_conditioning` reports the sine of each observed bend
   per bone per frame, so a report can say how much to trust each twist instead of reading
   a boolean.

Two **test expectations** were also wrong and are corrected in place with the measurement
that overturned them: a mirrored left/right reading does **not** round-trip cleanly (0.16
of the figure's height, not zero), and the first synthetic fixture's limbs carried a slight
rest kink that made the hinge datum non-perpendicular and put a few degrees of unexplained
error on every limb.

### 4.3 What the model holds at identity, and why

`spine` (no mid-torso landmark exists in the 33), `neck` (the 33 give one head frame, not
two), and the five facial markers (registered non-deforming — no vertex is weighted to
them). Each carries its reason in the solver's own output, not only in a docstring.

---

## 5. Stage B1 — through the real detector

Fixture: the banked walk authored onto the performer — 65 frames at 16 fps, `author_walk`'s
own gates green (D: 119 channels identical across two authorings; F: max 6.10e-06 against
an input floor of 7.04e-07; A: bones 5.58e-06, skin 1.66e-06). Rendered at **1920×1080**,
three-quarter front, camera solved by the banked framing module.

**The ground truth was checked before anything was quoted against it.** The full site set
rebuilt here from the authored angles agrees with the fixture's own sidecar landmarks to
**2.3e-16**.

### 5.1 Detection — the gate, and it passed

| quantity | measured |
|---|---|
| frames returning a pose | **65 / 65 (fire rate 1.000)** |
| mean visibility, all 33 landmarks × 65 frames | **0.8482** |
| mean visibility, the 9 face landmarks | **0.9999** |
| mean visibility, the 4 torso landmarks | **0.9999** |
| lowest per-landmark means | `left_elbow` **0.212**, `left_wrist` 0.318, `left_thumb` 0.324, `left_pinky` 0.326, `left_index` 0.348 |
| highest | `nose`, `right_eye*`, `right_hip`, `right_shoulder` — all **1.000** |

The overlay column of the sheet shows where the detector actually put its points, which is
the only instrument that catches a confident lock onto a shadow or a floor seam. It landed
on the figure.

### 5.2 The axis convention — measured, not assumed

| quantity | measured |
|---|---|
| assumed camera-derived basis vs per-frame best fit to ground truth | **median 16.26°**, p10 7.07°, p90 56.17°, 2 of 65 frames above 90° |
| best-fit RMS residual, landmarks as read | median **0.1196** (rig units; the figure spans 1.069) |
| best-fit RMS residual, left/right **mirrored** | median **0.1451** — worse, so the as-read handedness is the better fit and `SITE_FROM_LANDMARK` is right |
| detector→rig scale | median **0.6498**, range 0.259–0.723 |

### 5.3 Three gaps, told apart

Pooled over 17 gait bones × 65 frames = 1105 per-joint geodesic errors.

| arm | median | p90 | max |
|---|---|---|---|
| **model gap only** — authored ground-truth positions, no detector at all | **7.37°** | 60.99° | 83.95° |
| **detected, oracle axis fit** — detector, convention removed by fitting to ground truth | **34.33°** | 79.27° | 178.97° |
| **detected** — the deployable chain | **34.87°** | 79.65° | 178.97° |
| **detected, after one EMA pass** (α = 0.5, the single recorded lever) | **31.17°** | 67.55° | 177.52° |

By group (median):

| arm | arms | legs | torso |
|---|---|---|---|
| model gap only | 40.00° | 14.72° | **0.04°** |
| detected, oracle axis | 48.10° | 35.41° | 11.58° |
| detected | 48.10° | 35.41° | 11.89° |

**Where the axis convention actually lands.** The oracle arm differs from the deployable
one by 0.54° overall, and the whole difference sits at the root: `hips` reads 19.14° with
the oracle fit and **27.98°** without it, while every limb bone is identical to two decimal
places. Local rotations are relative to their parent, so a global mis-rotation of the input
is absorbed by the root and does not propagate — measured, not reasoned.

Worst and best bones on the deployable arm: `wrist.R` 69.65°, `elbow.L` 61.09°, `head`
53.51°, `hip.R` 51.18° … `chest` 12.21°, `ankle.R` 11.07°, `spine` 0.44°, `neck` 0.00°
(the last two are held at identity by the model, so their error is the authored magnitude
of what the model does not carry).

### 5.4 Position round-trip, on a body that is not the rig's

| arm | median | max |
|---|---|---|
| model gap only | **0.000262** | 0.000766 |
| detected | **0.2707** | 0.3673 |

Against a figure whose bbox diagonal is 1.069. The Stage A gate's tolerance, for scale, is
1.07e-09 — it is **not** armed here, and the spec says so: the observation comes from
another body, so a residual is the measurement rather than a defect.

### 5.5 Bone length — the other body, quantified

After removing the single global scale, per-bone residual as a fraction of that bone's own
rest length (median over 65 frames):

`wrist.L` **−0.744** · `wrist.R` −0.503 · `ankle.L` −0.453 · `shoulder.L` −0.440 ·
`shoulder.R` −0.282 · `knee.L` −0.266 · `hip.R` −0.225 · `elbow.L` **+0.213** …
**median |residual| over all 14 limb bones: 0.246.**

### 5.6 Feet — and a metric that cannot measure this population

`walk.foot_slip`'s headline is the slower foot's path divided by the hips' path. Premise 7
says MediaPipe world landmarks are hip-origin, so the hips barely translate and **the
denominator is structurally near zero**. Numerator and denominator, separately:

| series | slower-foot path | hips path | ratio | max per-contact slip |
|---|---|---|---|---|
| authored ground truth | 0.1770 | 1.2752 | 0.1388 | 0.2564 |
| model gap only | 0.1770 | 1.2752 | 0.1388 | 0.2564 |
| detected | 3.8515 | **0.1950** | 19.756 | 0.3370 |
| detected + one EMA pass | 2.5399 | **0.1950** | 13.028 | 0.2823 |

The authored row reproduces the fixture's own recorded 0.13882 exactly, so the instrument
is wired correctly. **The 19.756 is not quoted as a foot-slip reading** — grade an arm only
on what it can move, and this ratio's denominator is fixed near zero by the landmark
convention rather than by anything the lift does.

### 5.7 Jitter, and the twist ledger

Median-of-per-bone-medians of frame-to-frame rotation change: authored ground truth
**0.46°**, detected **16.69°**, detected after one EMA pass **7.08°** (p90s: 3.11°, 93.18°,
45.28°).

Twist underdetermined, frames out of 65: `wrist.L`, `wrist.R`, `ankle.L`, `ankle.R` —
**65/65 each**, nothing observed past their tails. Every other limb bone: **0/65**, with
median bend-sine from 0.162 (`shoulder.L`) to 0.989 (`knee.R`) and minima as low as 0.023,
which is the conditioning number the report carries rather than a boolean.

### 5.8 The applier ran

`tools/lift_solve.py` keyed the EMA-smoothed lift onto the performer's own rig and
exported: 65 frames, 154 f-curves, **Gate ARRIVED max 6.342e-06** against a tolerance of
1.069e-04, with Gate N clean before and after the round trip. Rendered on the identical
camera for the sheet.

### 5.9 The sheet

`outputs/E09/sheets/E09-B1-lift.png` (sha256 `9c74074d86ebbd28…`) — **source | what the
detector saw | the rig performing the solved lift**, frames 0/16/32/48/64, cropped to the
union of the subject's own pixels measured against the empty plate. Full 1920×1080 frames
stay on disk uncropped for the Director's zoom. Built before any number in §5.3 was
written into this report.

---

## 6. Stage B2 — HALTED before the first submission

**Premise 6 was marked ASSUMED, the spec required it verified in code before submission,
and the verification falsified it.** Then the replacement route failed the same check for
four independent reasons. Zero credits.

### 6.1 The named route does not exist in the form named

The spec's B2 says "832×480×65 on the saved-route shape (E02 A2 no-control precedent)". The
saved workflow `armature-E02-vace-control.json` was fetched and read: it is a **Wan 2.1
VACE** graph — `WanVaceToVideo`, `LoadVideo`, `Canny`, and a `LoadImage` reference plate,
24 nodes, seed 654654950714624, model `wan2.1_vace_14B_fp16.safetensors`. E02's A2 was that
graph with the control removed. **It is not a Wan 2.2 T2V shape and cannot carry a
text-to-video clip.**

### 6.2 The one served Wan 2.2 T2V route, checked in code

`video_wan2_2_14B_t2v` presents **4 nodes** and hides **30 inside a subgraph blueprint**.
`tools/armature_core/route_gates.py` was written to walk into subgraph definitions and
report, and `tests/test_route_gates.py` (16 tests) pins it. Run against the served graph,
**Gate ROUTE fired**. Evidence at `outputs/E09/route/route_gate_evidence.json`:

| finding | detail |
|---|---|
| **the licence map's excluded component is wired at full strength** | `wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors` and `…_low_noise.safetensors`, both `LoraLoaderModelOnly` at strength 1.0, both inside the subgraph. Apache-2.0, so licence-clean — but the map records them **excluded on methodology grounds**, and they are not even bypassed. The map's standing ruling is that presence is presence |
| **Gate S cannot be armed** | `KSamplerAdvanced` node 81 carries `control_after_generate = "randomize"`. A randomising seed is a seed no committed list pre-registered |
| **the spec's frame cannot be set** | the latent is `EmptyHunyuanLatentVideo [640, 640, 81, 1]`, and the frame count is *computed* inside the subgraph by `ComfyMathExpression 'floor(a * b) + 1'` from duration × fps primitives. The exposed slot list carries `width` and `height` and **no length and no seed** |
| **the trajectory is the excluded one** | both samplers run **4 steps at cfg 1** |

Gate L was run standalone and the spec's requested shape is legal: **832×480×65** — 832/16
= 52, 480/16 = 30, 65 = 4·16+1, ≤ 81 trained horizon. The shape is fine; there is no served
route on which it can be set.

### 6.3 Why this seat stopped rather than building one

Reaching the spec's B2 from here means deleting two LoRA loaders and rewiring around them,
moving the samplers off the 4-step/cfg-1 trajectory, defeating `randomize` and pinning a
seed, and re-pointing the frame-count computation. That is **rebuilding the route, not
running it** — and this repo halted E08 twice, at real cost, on exactly the shape of a seat
re-cutting a route under itself. The executor rules say stop at every gate and never
improvise past one; the advisor rules on what a fired gate means.

No seeds were pre-registered under any route, so **there is no Gate S surface to unwind**.
No uploads were made, so there is nothing on the server to delete.

---

## 7. Predictions versus outcomes

Blindness as disclosed in [E09-predictions.md](E09-predictions.md), registered at `e7b4db5`
before any measurement.

| clause | predicted | measured | outcome |
|---|---|---|---|
| **H1a** (not blind) position round-trip < 1e-9 of diagonal | — | < 1e-9, gate armed | **HIT** |
| **H1b** (not blind) rotation round-trip < 1e-9 rad | — | < 1e-9 rad | **HIT** |
| **H1c** (not blind) wrists/ankles always flagged underdetermined; the rest only when straight | — | wrists/ankles 65/65; every other limb bone 0/65 on this walk | **HIT** |
| "a miss on H1 is a bug, never a tuning target" | — | two misses, two bugs, both fixed | **HIT, expensively** |
| **H2a** BLIND — fires on ≥ 90 % of 65 frames | ≥ 59 | **65/65** | **HIT** |
| **H2b** BLIND — mean visibility in 0.50–0.90 | — | **0.8482** | **HIT** |
| **H2c** BLIND — face landmarks lower than torso | face < torso | face **0.9999**, torso **0.9999** | **MISS.** The reasoning was wrong, not just the number: I predicted a blank face would regress weak landmarks, and the detector is fully confident on the head. The weak landmarks are the **occluded far-side arm** — `left_elbow` 0.212 at a three-quarter view — which is about geometry, not about surface features |
| **H3a** BLIND — median per-joint error > 10° | — | **34.87°** | **HIT** |
| **H3b** BLIND — legs worse than arms | legs > arms | arms **48.10°**, legs **35.41°** | **MISS, and reversed.** The arms are the worse group in every arm of the decomposition, including the one with no detector in it |
| **H3c** BLIND — median \|bone-length residual\| > 10 % | — | **24.6 %** | **HIT** |
| **H3d** BLIND — model gap ≥ 3× smaller than detected | ≥ 3× | 7.37° vs 34.87° = **4.73×** | **HIT** |
| **H4a–c** (B2) | — | **NOT RUN** — Stage B2 halted | — |

Two of the four blind clauses in H2/H3 missed, and both misses were about *which* thing
would be weak rather than about magnitude.

Also recorded from the predictions' own "what would make me wrong in a way I would not
notice" list: the detector-locked-onto-a-shadow failure was checked by eye on the overlay
column and did not occur; the axis convention was measured rather than assumed and turned
out to be 16.26° off, which is exactly the silent-consistent-error the note warned about;
and the partial-firing population risk did not arise because the gate's clause is every
frame.

---

## 8. Artifacts

| artifact | path | sha256 (first 32) |
|---|---|---|
| walk fixture GLB | `outputs/E09/walk/performer_walk.glb` | `ef0dc34589b195bce38eaf8c6bbd5d40` |
| authored ground truth | `outputs/E09/walk/performer_walk.motion.json` | in the GLB's sidecar |
| source render, 65 × 1920×1080 | `outputs/E09/render-1080p/` | per-frame in `render_provenance.json` |
| detection record, raw | `outputs/E09/measure-b1/detection_raw.json` | — |
| measurements | `outputs/E09/measure-b1/measurement.json` | — |
| solved motion (raw, EMA) | `outputs/E09/measure-b1/lifted{,_ema}.motion.json` | — |
| lifted GLB | `outputs/E09/lifted/performer_lifted_ema.glb` | `33f68dd955434806c11332a262a71e7f` |
| lifted render | `outputs/E09/render-lifted/` | per-frame in its provenance |
| **the sheet** | `outputs/E09/sheets/E09-B1-lift.png` | `9c74074d86ebbd2874fac2f0f39a88f1` |
| route-gate evidence | `outputs/E09/route/route_gate_evidence.json` | — |
| served template, as fetched | `outputs/E09/route/video_wan2_2_14B_t2v.raw.json` | — |

`outputs/` is git-ignored by design; the record is this report, the provenance JSON and the
hashes above.

## 9. Compensators, as spent

| act | compensator | state |
|---|---|---|
| cloud credits | none exists | **nothing spent** |
| uploads to Comfy Cloud | delete server-side | **none made** |
| venv `E:\AI\armature\.venv` | `Remove-Item -Recurse` | created; owner executor |
| detector model at `E:\AI-Models\mediapipe\` | delete the file | downloaded, 30.7 MB |
| `outputs/E09/` | delete the directory | written; owner executor |
| worktree + branch `E09-run` | `git worktree remove` + branch delete | owner advisor, after the ruling |

No publishes, no releases, no external posts, no writes to the memory store, and nothing
written into facet's or E07's trees.

---
---

# Part 2 — Stage B2, run under amendment A2

**Appended 2026-08-11 by the same executor seat, after
[E09-calibration-ruling.md](E09-calibration-ruling.md).** Stages A and B1 above stand as
ruled; the B2 halt was upheld and B2 re-scoped to the clean in-repo graph commissioned by
R8. **One probe generation ran.** Measurements only; no judgement words. The Director
judges the sheet.

## 10. The meters, part 2

| meter | reading |
|---|---|
| **Credits** | **0 of the ceiling of 8.** `estimate_credits` on the exact graph, before submission: *"0 credits — no paid API nodes found in this workflow."* The route is entirely open weights, so it bills GPU-hours and **the credit ceiling is not the binding meter on it**. Premise 5's 4-credits-per-generation number was measured on E02's route and does not transfer. Ledger: one submission, `prompt_id 8cf803af-ff3c-4a43-beee-b2d529850627`, reserve unspent |
| **GPU-hours (cloud)** | **NOT YET REFLECTED IN THE INVOICE.** The workspace's 2026-08-11 *GPU Hours Product* bucket read `$3.636348` both before and after the run — the invoice-backed report lags. This is recorded as *not yet visible*, not as zero. The measurable proxy is wall clock: submitted, then terminal on the eighth `wait_for_job` poll, so **queue + execution ran roughly 3–4 minutes** for 40 steps across two 14B experts at 832×480×65 |
| **GPU (local)** | Two further headless Blender passes: the applier on the solved dance, and a 65-frame 1920×1080 render of the rig performing it |

## 11. Gate states, part 2

| gate | state |
|---|---|
| watchdog liveness | **PASS** — re-verified before any GPU work this session |
| licence pin | **PASS** — no new dependency. All four weights are map-covered; the fp8-scaled files are Comfy-Org repacks of the mapped Apache weights under the map's 2026-08-11 repack ruling. **No LoRA of any kind is loaded** |
| **Gate ROUTE** | **PASS, twice** — on the API graph we built, and again on the save-format file the cloud returned, because "submit the saved file verbatim" only means something if the saved file is what was checked. 4 weight files, 2 seeds pinned, 1 latent legal |
| **Gate S** | **PASS** — seed list committed at `1017558`, *before* the graph was built. One noise-bearing seed, `20260811`, pinned `fixed`, drawn from the committed list; the low-noise expert's seed is inert (`add_noise=disable`) and is reported rather than demanded |
| **Gate L** | **PASS on the actual graph** — 832×480×65: 832/16 = 52, 480/16 = 30, 65 = 4·16+1, ≤ 81 |
| **Gate C** | **PASS** — priced at 0 credits before submission; ceiling 8 not approached |
| dry-run pre-flight | **PASS**, no warnings — and it did *not* stand in for the in-code checks, per CLAUDE.md |
| **detection** (B2) | **PASS — a pose on 65 of 65 frames** |
| **lossless tap** | **PASS** — 65 PNGs straight off the `VAEDecode`, which is what the review was cut from |
| Gate N / OBJ / SPACE / MOTION_RECORD / ARRIVED | **PASS** — applier on the solved dance, `ARRIVED` max 5.348e-06 against 1.069e-04 |
| Blender success-sentinel | **PASS** on both invocations |

## 12. The graph, and where every number came from

Built in-repo, 15 nodes, sha256 `7e8b8877abfc118d…`. Saved as
`armature-E09-B2-t2v-clean`; the save→convert round trip changed nothing (node 50 came back
byte-equal on every input).

Fetched verbatim from Wan-Video/Wan2.2 (Apache-2.0) and kept beside the graph:

| value | from |
|---|---|
| `sample_steps = 40` | `wan/configs/wan_t2v_A14B.py` |
| `sample_shift = 12.0` | same |
| `boundary = 0.875` | same |
| `sample_guide_scale = (3.0, 4.0)  # low noise, high noise` | same — so cfg 4.0 on the high-noise expert, 3.0 on the low |
| `num_train_timesteps = 1000`, `sample_fps = 16`, `sample_neg_prompt` | `wan/configs/shared_config.py`, negative used verbatim |
| `euler` / `simple` | **neither source** — a port necessity, recorded as one: the reference's `unipc` solver has no ComfyUI equivalent for this graph |

**The two-expert split is derived, not dialled.** The reference switches on the *timestep*
(`t ≥ boundary · num_train_timesteps`); ComfyUI splits on a step index. With
`σ' = shift·σ/(1 + (shift−1)·σ)` and `simple` stepping σ linearly 1→0, the crossing lands
at **step 26 of 40** — high-noise 0..26, low-noise 26..40. The whole 41-row schedule is in
the payload record. The served template's own 2-of-4 split is not the reference's and was
not used.

**Prompt, verbatim** (recorded because a paraphrased prompt is a different experiment):

> A single dancer alone in an empty studio, filmed head to feet in one continuous mid-shot.
> She dances slowly and evenly, facing the camera, with her arms held out away from her body
> and her legs apart, so that her arms and legs stay clear of her torso and never cross or
> overlap each other. Plain flat pale grey backdrop, even soft studio lighting, no props, no
> furniture. The camera does not move. One person only, whole body visible in frame at all
> times.

## 13. A scrambling defect caught before any measurement

`get_output` returns **content-addressed filenames** — `00f09b64…`, `0211117d…` — so
sorting them alphabetically produces a random frame order. The first download did exactly
that. Every count would have been right (65 frames), every gate would have passed, and the
lift would have been measured on a **shuffled clip**, with the resulting jitter read as
detector noise.

Caught and settled by measurement rather than by assumption: mean consecutive-frame
absolute pixel difference is **0.703** in the results-array order and **5.314** sorted —
7.6× apart. The array order is temporal; the sequence was rewritten in it, and the evidence
is at `outputs/E09/b2-probe/frame_order_evidence.json`.

## 14. What the generation produced — measured, not graded

| observation | measurement |
|---|---|
| single person, plain backdrop, static camera, arms clear of the torso, legs apart | all present |
| **the body is cropped above the ankle** | all six lower-leg landmarks (`left/right_ankle`, `left/right_heel`, `left/right_foot_index`) lie **outside the image on 100 % of frames**; knees outside on 25 % (L) and 34 % (R). "head to feet" and "whole body visible in frame at all times" were asked for and not delivered |
| rendering | a backlit near-silhouette against a high-key backdrop |
| motion magnitude | mean consecutive-frame pixel difference **0.703 / 255** — the dancer is close to static in a held second position |

## 15. B2 measurements

### 15.1 Detection — the gate, and it passed

| quantity | B2 (generated dancer) | B1 (rendered mannequin) |
|---|---|---|
| frames returning a pose | **65 / 65** | 65 / 65 |
| mean visibility, all 33 | **0.8613** | 0.8482 |
| face landmarks | **1.0000** | 0.9999 |
| torso landmarks | **0.9991** | 0.9999 |
| **lower-leg landmarks** | **0.3058** | — |
| lowest per-landmark | `right_heel` 0.219, `left_heel` 0.242, `right_foot_index` 0.278, `right_ankle` 0.325 | `left_elbow` 0.212 |

The weak landmarks moved from B1's occluded far-side arm to B2's **cropped-away feet**. In
both cases the weakness is geometric — what the frame does or does not contain — not the
surface detail I predicted in H2c.

### 15.2 Scale, bone length, round trip

Detector→rig scale **0.8718**, from a pose-invariant summed-bone-length ratio (B1 fitted
this against ground truth; B2 has none, so the method differs and is recorded).

Per-bone residual after removing that scale, median over 65 frames: `elbow.R` **+0.629**,
`ankle.L` −0.518, `wrist.L` −0.474, `elbow.L` +0.458, `shoulder.L` −0.364, `hip.L` +0.361 …
**median |residual| over all 14 limb bones: 0.298** (B1: 0.246).

Position round-trip on the solved rotations: median **0.3203**, max 0.3292, against a
figure whose bbox diagonal is 1.069 (B1 detected: 0.2707). No gate — the observation comes
from another body entirely.

### 15.3 Jitter

| series | median-of-medians | median-of-p90 | max |
|---|---|---|---|
| B2 detected | **0.539°** | 1.525° | 176.749° |
| B2 after one EMA pass (α = 0.5) | **0.409°** | 1.126° | 124.135° |
| B1 detected, for comparison | 16.69° | 93.18° | — |
| B1 authored ground truth | 0.46° | 3.11° | — |

Worst B2 bones: `shoulder.L` 4.06°, `elbow.L` 2.73°, `knee.L` 1.38°, `knee.R` 1.24°.

### 15.4 Twist

`wrist.L`, `wrist.R`, `ankle.L`, `ankle.R` — underdetermined **65/65** each, as in B1.
Every other limb bone 0/65, with bend-sine medians from **0.0706** (`shoulder.L` — the
arms are held nearly straight, so its twist is the worst-conditioned on the clip) to
0.9922 (`knee.R`).

### 15.5 Feet

The ratio is **not quoted as a reading** — R3 ruled it valid on world-rooted motion and
invalid on hip-origin lifted motion. Numerator and denominator separately:

| series | slower-foot path | hips path | max per-contact slip |
|---|---|---|---|
| B2 detected | 0.2483 | 0.0035 | 0.0442 |
| B2 + one EMA pass | 0.1482 | 0.0035 | 0.0506 |
| B1 detected, for comparison | 3.8515 | 0.1950 | 0.3370 |

The denominator is 0.0035 — the hips are effectively fixed, which is what a hip-origin
landmark stream on a dancer who does not travel produces.

### 15.6 The axis convention — assumed here, and the assumption is named

B2 has no camera record, so the basis is the frontal-camera convention, **ASSUMED**. B1
measured what that assumption costs on a *known* camera: median 16.26° off the best fit,
landing almost entirely on the root (`hips` 27.98° vs 19.14° with an oracle fit) with every
limb bone identical to two decimal places. Root motion is out of scope (premise 7), so the
limbs — which is what a dance is — carry the cost B1 measured for them, which was none.

## 16. The Gate 0 sheet, and the review materials

`outputs/E09/sheets/E09-B2-gate0.png` (sha256 `74794aadb2198796…`) — **source | what the
detector saw | the performer's rig performing the solved lift**, frames 0/16/32/48/64,
built before any number above was written into this report.

The source column is shown **uncropped at 832×480** and the reason is recorded on the sheet
itself: a generated clip has no empty plate to difference against, and cropping to the
detector's own landmarks would let the instrument on trial choose what the Director sees.
The lifted column is cropped against its own empty plate.

Review materials, from `lossless/` and nothing else:

- `outputs/E09/b2-review/review_0.5x_8fps.webp` — **lossless** animated WEBP, 8 fps against
  a 16 fps source = **0.50×**, native 832×480, 65 frames.
- 20 native-resolution stills at frames 0/16/32/48/64 on both hands and both feet.
  **Hands: in frame on 5 of 5 stills. Feet: outside the image on 5 of 5** — the still is
  cut anyway and the sidecar records that the landmark was outside, because that is the
  finding rather than a missing file.

Per R2, the arms are what a dance is and are inspected first: `shoulder.L` carries the
clip's worst twist conditioning (bend-sine median 0.0706) and its largest jitter (4.06°).

## 17. Predictions H4 versus outcomes

Registered blind at `e7b4db5`, before any B2 work.

| clause | predicted | measured | outcome |
|---|---|---|---|
| **H4a** — frame-to-frame solved-rotation change larger on the generated clip than on the rendered fixture | B2 > B1 | B2 **0.539°** vs B1 **16.69°** — B2 is **31× smaller** | **MISS, and reversed.** The prediction assumed a generated dance would move at least as much as the authored walk. The measured confound is in the source itself: mean consecutive-frame pixel difference 0.703/255, i.e. the dancer is nearly static, so there is little motion for jitter to ride on |
| **H4b** — the foot-slip diagnostic on the solved dance exceeds the fixture's | B2 > B1 | max per-contact slip B2 **0.0442** vs B1 **0.3370**; numerator 0.2483 vs 3.8515 | **MISS on the stated comparison.** Feet were the defect class, but for a reason the prediction did not name: they were **never observed at all** — outside the image on 100 % of frames — so the foot landmarks are extrapolations, not slippage |
| **H4c** — no threshold offered; numerator and denominator reported separately; worth-a-shot is the Director's call | — | held throughout | **HELD** |

Three of the six blind clauses across H2/H3/H4 have now missed, and every one of them
missed on *which thing would be weak* rather than on magnitude.

## 18. Artifacts, part 2

| artifact | path | sha256 (first 32) |
|---|---|---|
| the graph, as built | `outputs/E09/route/E09-B2-t2v.api.json` | `7e8b8877abfc118d1daf3c9c668c9318` |
| payload record (every value + its source, the 41-row schedule) | `outputs/E09/route/E09-B2-payload-record.json` | — |
| admission on the saved file | `outputs/E09/route/E09-B2-saved-admission.json` | — |
| Wan 2.2 reference configs, as fetched | `outputs/E09/route/wan22_{shared_config,t2v_A14B}.py` | `3ae102e029d4d0e3…`, `a1f3a70472aece6d…` |
| **65 lossless frames** | `outputs/E09/b2-probe/lossless/` | per-frame in `lossless_manifest.json` |
| frame-order evidence | `outputs/E09/b2-probe/frame_order_evidence.json` | — |
| probe mp4 (convenience only) | `outputs/E09/b2-probe/probe.mp4` | `1b54f0a4eade8c2798df6afeaafdfefd` |
| detection record | `outputs/E09/b2-measure/detection_raw.json` | — |
| B2 measurements | `outputs/E09/b2-measure/measurement.json` | — |
| solved motion (raw, EMA) | `outputs/E09/b2-measure/lifted{,_ema}.motion.json` | — |
| the rig performing the dance | `outputs/E09/b2-lifted/performer_dance_ema.glb` | `9aebeeb8e60da914aa0a2a49541bab7d` |
| **the Gate 0 sheet** | `outputs/E09/sheets/E09-B2-gate0.png` | `74794aadb21987968b70b875788dde51` |
| **the review clip, lossless 0.5×** | `outputs/E09/b2-review/review_0.5x_8fps.webp` | `2886431deed0900c87b24dbb2e244d8b` |

Suite after B2: **442 passed, 35 skipped.**

## 19. Compensators, part 2

| act | compensator | state |
|---|---|---|
| the probe generation | **none exists** — spent GPU-hours have no undo | one generation, reserve unspent |
| saved cloud workflow `armature-E09-B2-t2v-clean` | delete server-side | present; owner executor |
| downloaded outputs under `outputs/E09/b2-*` | delete the directories | written; owner executor |
| `E:\AI-Models\mediapipe\pose_landmarker_heavy.task` | delete the file | unchanged from part 1 |
| worktree + branch `E09-run` | `git worktree remove` + branch delete | owner advisor, after the ruling |

No uploads were made (the graph is text-to-video and takes no input files). No publishes,
no releases, no external posts, no writes to the memory store.

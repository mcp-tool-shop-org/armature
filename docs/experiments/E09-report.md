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

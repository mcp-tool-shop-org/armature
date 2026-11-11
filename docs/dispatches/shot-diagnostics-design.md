# Shot diagnostics — design: camera error and masked identity

**Card:** R&D → Antigravity, 2026-11-11, Part 1 (DESIGN only). **Branch:** `feat/shot-diagnostics`,
cut from `main` at `fee4f74`. **Status:** a design. Nothing here is built, and nothing was run:
the card is FILES ONLY until R&D writes CARD FREE, and it loads no model at any point. Every
number in §6 that was not read off a source is marked **[Guess]**.

**Trajectory.** This card spends no credits, so the row is not a spend gate here; it is written
anyway. These two instruments advance the full scope ("footage from a scene you own",
`CLAUDE.md:14-17`) by making two questions measurable on any generated shot, whatever it is for:
*did the model shoot the camera we authored*, and *what does the subject region alone look like
next to the reference*. The first is geometry the previz already knows exactly; the second is a
diagnostic only, under the law below.

---

## 0. The law this design obeys, quoted

**Identity is the product** (`CLAUDE.md:191-200`):

> Identity and quality diagnostics ride reports as diagnostics and **may gate nothing**.
> (`CLAUDE.md:196`)
>
> Stylized game characters may break face-embedding tools outright; a diagnostic that returns
> numbers on a face it cannot find is noise wearing a unit. Any such number is quoted with
> evidence that its detector actually fired. (`CLAUDE.md:198-200`)

and its earning story, which binds the masked-identity half directly: "no metric approximates it
(facet learned this twice, once with high-pass statistics for material identity and once with
silhouette IoU for character identity)" (`CLAUDE.md:194-195`).

**The licence gate** (`CLAUDE.md:171-189`):

> **No non-commercially-licensed model, weight, LoRA, preprocessor, or code dependency anywhere
> in the pipeline — including experiments.** (`CLAUDE.md:173-174`)
>
> A license that cannot be retrieved is **UNVERIFIED — treat as NO**. (`CLAUDE.md:185`)
>
> **The same family can split across variants** — check the exact variant and version you are
> about to run, not the family name. (`CLAUDE.md:188-189`)
>
> **CONDITIONAL is a Director decision**, surfaced contrastively, never silently accepted.
> (`CLAUDE.md:182`)

Also binding on this design, each cited where it is used: gates raise and a diagnostic is a
different object (`CLAUDE.md:142-147`); metrics are diagnostics (`CLAUDE.md:167`); suspend rather
than invent a threshold (`CLAUDE.md:106-111`); grade an arm only on what it can move
(`CLAUDE.md:159-161`); a licence row is not a wiring claim — name the exact weight files loaded
(`CLAUDE.md:283-288`); a placeholder shaped like evidence is banned — write `NOT YET RUN`
(`CLAUDE.md:162-164`).

---

## 1. Where these fit

### 1.1 The existing instruments they sit beside

| existing | what it already says | how the new diagnostics relate |
|---|---|---|
| `clipstats.horizon_row` (`tools/armature_core/clipstats.py:21-31`, def `:274`) | "the one here that separates camera from subject"; returns `None` with an agreement figure when the room is repainted (`:27-31`) | **Camera error is its quantitative successor.** The horizon row says *whether* the camera moved on frames where a horizon exists; camera error says *how far from the authored camera*, in degrees, on frames where features exist. Same failure honesty: no number where the instrument cannot read. |
| `measure_clip` (`tools/measure_clip.py:96-118`, record status `:148-151`) | whole-image stats, "it measures; it judges nothing" (`:8-10`) | The new CLI copies its shape: numbered lossless frames in, one JSON out, `status: "DIAGNOSTIC — every number here gates nothing"`, the shared halt handler (`:185-191`). |
| `clipstats.frame_deltas` / `similarity_to_first` (`clipstats.py:15-19`) | "conflated by construction" — subject, camera, exposure, repaint | **Masked identity is the subject-only counterpart.** Whole-frame similarity moves with the background; the masked crop is the attempt to remove that, and it stays a diagnostic. |
| `measure_tracking` (`tools/measure_tracking.py:38-42`) | timing correlation; "says nothing about whether it is the same character. **It gates nothing**" | sits in the same diagnostics block on the sheet. |
| `clipstats.motion_aware_diagnostics` (`clipstats.py:464-551`) | lift/pose-unit diagnostics graded in their own units, not pixel deltas | precedent for grading in the quantity's own unit: camera error is graded in degrees and scale-free ratios, not pixels. |
| `donor_gate` fired-only fraction (`tools/armature_core/donor_gate.py:32-35`, `:251-300`) | the fired-only population is carried "beside the gating one, as a diagnostic" | **the precedent for "detector fired"**: report the population the instrument actually read, by count, next to the number. |
| `make_identity_sheet` (`tools/make_identity_sheet.py:7-13`) | "this tool computes nothing and decides nothing… the judgement is the Director's" | masked identity never replaces this sheet; its tiles go *under* it as labelled diagnostics. |
| `errors.GateCanon` (`tools/armature_core/errors.py:299-307`) | "Identity diagnostics still gate nothing" | the masked-identity module raises no `GateFailure` on any score value, by construction (§3.4). |

### 1.2 Where the new code would live (proposal for Part 2)

* `tools/armature_core/shotdiag.py` — pure core, no bpy, no torch: numpy + `cv2` (both already
  runtime dependencies, `pyproject.toml:139-144`). Camera conventions, intrinsics, the classical
  recovery, alignment, error metrics, masked cropping, fired evidence, floors, the record shape.
  Refusals subclass `ArmatureError` with `gate: None` + `andon` + `clause`, the shape
  `ClipStatsError` uses (`clipstats.py:42-66`).
* `tools/measure_shot.py` — CLI in `measure_clip`'s shape: `--frames=<lossless dir>`
  `--render-run=<stage_render run dir>` `--reference=<alpha reference dir>` `--out=<json>`;
  prints `MEASURE_SHOT_OK`; halt contract via `armature_core.parts.run_tool_main`.
* A licence load gate for measurement weights (§4.3), the one true gate in this design: it decides
  whether a weight file is loaded at all, which is the step the licence gate exists to stop.
* Report surfaces: `sheet_compose.diagnostic_lines` (`tools/sheet_compose.py:97-103`) gains a
  `measure_shot` branch, and `make_thesis_sheet` (`tools/make_thesis_sheet.py:93-97`, `:200-213`)
  and `make_startframe_sheet`'s "MEASURED (diagnostics; they gate nothing)" block
  (`tools/make_startframe_sheet.py:124-128`) can take `--shot-diagnostics=<json>`.
* `docs/tools.md` gets a row beside `measure_clip` / `measure_tracking` (`docs/tools.md:54`, `:58`).

### 1.3 How a report shows them

Camera **before** identity, and identity never without camera. In the JSON the `camera` block is
written first; in the sheet lines the camera lines print first. The CLI **refuses**
(`ShotDiagError`, clause `identity_without_camera_block`) to write an identity block into a record
that carries no camera block — including a camera block that reads `NOT FIRED`. That refusal is
about the record's *shape*, never about a value, so it gates nothing the law protects.

Example of the lines a sheet would print (values illustrative of the *format* only):

```
MEASURED (diagnostics; they gate nothing)
shot.camera      fired 76/80 pairs  rot err med 1.9° / p90 3.4°  (GT span 30.0°)  est/GT span 0.93
shot.camera      t-dir err med 6.1° on 71/80 (9 rotation-only, t unobservable)  followed: NO THRESHOLD
shot.camera      floor (render through estimator) rot err med 0.4°  NOT A VERDICT
shot.identity    masked DINOv2-B/14  fired 78/81 frames  med 0.71  [decoy max 0.52 · bg max 0.31]
shot.identity    DIAGNOSTIC — gates nothing; identity is judged by eye on the sheet above
```

Before any of these is quoted, the control | output | reference | provenance sheet exists
(`CLAUDE.md:222-225`); the diagnostics are lines under its provenance, not a replacement for it.

---

## 2. Camera error

### 2.1 Ground truth: what armature already knows

* **Per-frame extrinsics:** `stage_render` records `camera_matrix` per frame, the Blender
  camera-to-world `matrix_world` (`tools/stage_render.py:290`, written into each frame record at
  `:397-409`, into `manifest.json` at `:590`). Blender's camera looks down its local −Z with +Y up
  (`tools/armature_core/framing.py:262-282`).
* **Intrinsics:** `lens_mm`, `sensor_mm`, `width`, `height` in the spec (defaults 50 / 36,
  `tools/armature_core/shotspec.py:73-87`), under Blender's AUTO sensor fit: the sensor spans the
  **longer** image axis (`framing.py:152-207`, the copy pinned against `blender_scene.half_fovs`).
  So `fx = fy = f_px = lens_mm / sensor_mm × max(width, height)`, `cx = width/2`, `cy = height/2`.
  The core computes `f_px` *from* `framing.half_fovs` (`f_px = (width/2) / tan(hx)`) rather than
  re-deriving the AUTO-fit rule, so one rule has one home.
* **Mask:** `stage_render` writes the `mask` channel (`CHANNEL_DIRS`, `stage_render.py:83-89`;
  `mask_from_alpha` at `:387`) and records `mask_px` / `mask_bbox` per frame (`:403-404`).
* **Static requests need no render.** The camera-i2v route imposes a `Static` trajectory
  (`tools/build_camera_i2v_payload.py:52-54`); its GT is the identity motion. E11 wave 1 recorded
  exactly the failure this instrument targets: "an uncommanded push-in; the horizon found on 4 of
  65 frames" (`build_camera_i2v_payload.py:54`).

**Premise, measured by reading (not by running):** `stage_render` is the only renderer in the tree
that records a per-frame camera matrix. `render_performer` and `preview_walk` record none (searched
for `camera_matrix` in both). See §8 for what that means for path shots.

### 2.2 Recovery method — two tiers behind one interface

**Tier A (proposed for the Part 2 build): classical two-view geometry, no learned weights.**
OpenCV (Apache-2.0, already a runtime dependency) on CPU:

1. Detect SIFT features on every generated frame (in OpenCV's main module since 4.4, patent
   expired; no `nonfree` build needed).
2. **Exclude the character.** Features inside the frame's dilated Blender mask are dropped: the
   performer moves independently of the camera and violates the static-scene assumption every
   two-view solver makes. Dilation is a fraction of the frame's own mask bbox, not a global pixel
   constant (`CLAUDE.md:157-158`).
3. Match each frame *t* to frame 0 (and to *t−1*, for a chained second reading), ratio test, then
   fit **both** an essential matrix with the known `K` (`findEssentialMat` + `recoverPose`, RANSAC)
   **and** a homography. Model selection by which explains the inliers (GRIC-style score):
   * E wins → relative rotation `R` and unit translation direction `t̂`;
   * H wins → the motion is rotation-only (or the background is one plane): `R` from
     `K⁻¹HK` projected onto SO(3); `t̂` is reported **unobservable**, never a number.
4. Record per pair: number of matches, inliers, chosen model, both model scores.

Why Tier A first: it needs no weight file, so the licence question is OpenCV's alone; it runs on
CPU while the GPU is busy; and its failure is legible (too few inliers → NOT FIRED), which a
feed-forward network's is not. Its known weakness is a repainted, textureless or non-rigid
background; that weakness is *reported* (fired counts), not hidden.

**Tier B (later, through R&D and the Publisher's grant): a feed-forward multi-view estimator.**
The only candidate this design finds licence-clean today is **MapAnything, Apache variant**
(`facebook/map-anything-apache`, §4). It accepts images **plus known intrinsics** and returns
OpenCV-convention cam-to-world poses (MapAnything README, "Images + Camera Intrinsics"; output
`camera_poses` "+X Right, +Y Down, +Z Forward"). Tier B is a second reading of the same quantity,
compared against Tier A on the same fixtures and the same clips; it is never wired until its row
is in the map and its exact weight file is named (`CLAUDE.md:283-288`). VGGT, MonST3R,
DUSt3R/MASt3R, CUT3R and VGGT-Omega are excluded on licence (§4).

### 2.3 Inputs and outputs

**Inputs:** the generated clip's lossless frames (`NNNNN.png`, the `VAEDecode` tap — never a
re-encode, `clipstats.py:3-4`); the `stage_render` run directory (manifest with per-frame
`camera_matrix`, spec intrinsics, `mask/`); or, for a Static request, the declaration `--static`.

**Refusals before any number** (each a named clause, `gate: None`): frame counts differ and no
explicit index map is given (`clipstats.motion_aware_diagnostics` records `length_match` the same
way, `clipstats.py:543`); aspect ratios differ (an unknown crop makes `K` unknowable); generated
resolution differs at the same aspect → `K` is **scaled**, and the scale is written into the
record; manifest carries no `camera_matrix` → `no_ground_truth_camera`.

**Output, the `camera` block:**

* per frame *t*: `fired` (bool), `n_matches`, `n_inliers`, `model` (`E` / `H` / `none`),
  `rot_err_deg` (geodesic angle between estimated and GT relative rotation; `null` when not
  fired), `tdir_err_deg` (angle between unit translation directions; `null` when not fired or `H`
  won), `gt_rot_from_f0_deg`, `est_rot_from_f0_deg`;
* clip summary over **fired frames only, with the fired count beside it** (`donor_gate`'s rule):
  median / p90 / max rotation error, the same for direction error, `gt_rot_span_deg`,
  `est_rot_span_deg` and their ratio (the "camera ignored" signature: a 30° orbit read as 2°),
  RPE between consecutive frames, the one fitted scale factor and the scale-fitted ATE;
* **parallax evidence for Static requests**, in pixels: the median residual of the homography
  model on background inliers. Zero for a camera that only rotates or holds; positive for one that
  translates. It is scale-free, which is exactly why it is there: a push-in has no metric size
  without scale, but its parallax is visible;
* `followed`: the literal `"NO THRESHOLD — CALIBRATION NOT YET RUN"` until §2.5 runs. Never a
  boolean before then.

### 2.4 Scale ambiguity and alignment — fit as little as possible

A monocular reconstruction is defined up to a similarity transform (7 DoF). Fitting all 7 onto GT
(Umeyama / Sim(3)) would **absorb rotation error into the fit** — the exact error this instrument
exists to report. So:

1. **Gauge by anchoring, not fitting.** Both trajectories are expressed relative to their own frame
   0: `R_rel(t) = R(0)ᵀ R(t)`, likewise for centres. That removes the world frame with zero fitted
   parameters.
2. **Rotation error is gauge-free and scale-free:** `angle(R_est_rel(t)ᵀ · R_gt_rel(t))`. Nothing
   is fitted.
3. **Translation direction is scale-free:** angle between `t̂_est(t)` and `t̂_gt(t)`, both in the
   frame-0 camera frame. Nothing is fitted.
4. **One parameter only, for ATE:** a single global scale `s` by least squares on the anchored
   camera centres. `s` is itself reported; a scale that is not one number across the clip shows up
   as ATE, not as a silently better fit.
5. **Convention conversion is explicit and tested:** Blender `matrix_world` (cam→world, −Z
   forward, +Y up) → OpenCV (cam→world, +Z forward, +Y down) by `diag(1, −1, −1)` on the camera
   axes. A missing flip reads as ~180°-class errors; a test pins it (§5, C4).

### 2.5 What "camera followed" means, and how its threshold would be set from data

**Definition (unit the experiment cannot move).** "Followed" is a statement about the rotation
error trajectory against the GT's own span, both fixed by the spec before generation: per frame,
`rot_err_deg(t)`, and per clip, `rot_err / gt_rot_span` (a fraction of the shot's own motion, per
`CLAUDE.md:157-158`) plus absolute degrees for Static shots, whose span is zero. Translation
direction and parallax are reported beside it, not folded in.

**The threshold is not set in this card and is not guessed.** Under `CLAUDE.md:106-111` the build
reports numerator and denominator and the literal NO THRESHOLD. A later spec sets it, from three
populations measured *before* the threshold is written and never retuned after:

| population | what it is | what it bounds |
|---|---|---|
| **F0 — instrument floor** | the Blender renders of a shot, through the estimator, against their own GT; then the same after the `yuv420p` round trip and resize to generator resolution (`clipcompare.py:11-14` records where that codec puts its error) | the error a perfectly-followed camera still reads |
| **N — known not-followed** | the same renders scored against a deliberately wrong GT: sweep reversed, static, another shot's path; plus any banked clip whose camera failure is already on record (E11 wave 1, if its frames are on disk) | the error a definitely-wrong camera reads |
| **G — generated, labelled by eye** | real generations the Director labels followed / not followed *before* their numbers are shown | where real clips fall |

If F0∪G_followed and N∪G_not separate, the threshold goes in the gap and is fixed in the spec. If
they overlap, there is no threshold: the diagnostic stays a reading and the overlap is the finding.
The noise floor is measured before any difference is read (`CLAUDE.md:150-152`).

### 2.6 Hard check or diagnostic? — the argument, for R&D's ruling

The card asks whether camera error may be a hard check because it is geometry, not identity.
Argued from the text:

**For a check.** The identity clause binds "identity and quality diagnostics" (`CLAUDE.md:196`).
Camera error is neither: the authored camera is a ground truth the repo *owns*, exactly — the
previz is ground truth (`CLAUDE.md:7`) — not a canon only the Director holds. Its letter does not
forbid gating on it.

**Against a check, today — four reasons from the text:**

1. "**Metrics are diagnostics; the Director's eye is the judge.**" (`CLAUDE.md:167`) — written for
   everyone, not only for identity. Camera error is a metric.
2. A gate "decides whether an irreversible step proceeds" and lives *inside the tool performing
   that step* (`CLAUDE.md:142-147`). Camera error is measured **after** the credits are spent; there
   is no irreversible step downstream of it in the pipeline today for it to stand in front of.
   A "gate" with nothing to stop is a verdict on output quality, which an executor may not issue
   (`CLAUDE.md:77-79`).
3. There is no calibrated threshold, and the law says to suspend rather than invent one
   (`CLAUDE.md:106-111`). Until §2.5 runs, any pass/fail line would be invented.
4. The estimator reads a background the model *painted*. Repainted or non-rigid backgrounds are
   exactly where two-view geometry fails; "a number from a detector that did not fire is noise"
   applies to a pose estimator as much as to a face embedder (`CLAUDE.md:198-200`, by its reasoning
   if not its letter).

**Recommendation:** **diagnostic now.** It could become a gate only when all three hold: the
threshold exists from §2.5's populations; there is a named irreversible step it precedes (for
example, the next batch of a cascade, or an adoption ruling); and R&D/the Director rule it.
What *is* a hard check in this design, and should be: the refusals in §2.3 (no GT, mismatched
frame counts, unknowable `K`) and the record-shape refusal in §1.3 — they refuse to produce a
number, never on a number's value — and the licence load gate in §4.3.

**STOP: R&D's ruling is asked for on this point** (decision D1, §10).

---

## 3. Masked identity

### 3.1 Method

**Primary: DINOv2 ViT-B/14 embeddings on masked crops** (`facebook/dinov2-base`, Apache-2.0, §4).
DINO, not CLIP, is already the repo's recorded lead: "VBench scores subject consistency with DINO
embeddings rather than CLIP… DINO is sensitive to identity difference… If a diagnostic is wanted,
DINO cosine — not CLIP-I" (`docs/research-grounding.md:105-108`). Two readings per frame:

* **CLS cosine** of the masked crop against each reference view;
* **masked patch-token similarity**: mean best-match cosine of in-mask patch tokens to the
  reference's in-alpha patch tokens (DINOv2's 14-px patch grid makes "in-mask" a per-token
  decision, so background tokens are excluded inside the network's own unit, not only by pixels).

**Second opinion, deferred:** DreamSim's `dinov2_vitb14` variant — its weights' licence is
UNVERIFIED as a separate grant (§4), so it does not enter until R&D rules on that residual.

**Not used:** CLIP (the repo's own finding above; and the OpenAI card's "Any deployed use case…
is currently out of scope" statement, §4); any face embedder — ArcFace/InsightFace models are
non-commercial at source (§4), and photo-face recognizers collapse on stylisation
(`docs/research-grounding.md:110-117`).

### 3.2 How armature's own masks crop the frames

* **Reference side:** the canonical reference views (the 8-view turnaround, per
  `docs/research-grounding.md:99-103`) are authored **RGBA with real alpha** (`CLAUDE.md:292-299`).
  The alpha is the exact mask; the crop is the alpha bbox plus a margin proportional to that bbox;
  outside-alpha pixels are composited over one recorded neutral plate.
* **Generated side:** the generated frame is cropped by the **Blender mask of the same frame**
  (`stage_render` `mask/`, `mask_bbox` recorded per frame, `stage_render.py:403-404`), same
  margin rule; outside-mask pixels are replaced by the same neutral plate; then resized to the
  model input. The record carries the plate value, the margin rule, and each frame's `mask_px`.
* **What the Blender mask is, stated plainly:** it is where the character *should* be — the
  previz silhouette — not a segmentation of the generated frame. If the model displaced the
  character, the crop holds background. That case is **meant** to read NOT FIRED (§3.3); it is
  not corrected for. A segmenter on the generated frame (SAM 2.1, BiRefNet — both re-fetched
  today, §4) could report *placement* agreement later; if it ever does, its IoU is a placement
  reading and is never quoted as identity (`CLAUDE.md:194-195`).

### 3.3 "Detector fired", for stylised and non-human characters

DINOv2 is not a detector: it returns a vector for anything, a robot, a slime, a sword. So
"fired" cannot mean "a face was found". It is defined as two pieces of evidence, both recorded
per frame, model-agnostic, and neither a tuned number:

1. **Occupancy:** the frame's Blender mask covers at least one full patch at model input (one
   14×14 token). Below that, there is no token the crop can be about. Structural, not tuned.
   Frames that fail are counted and get `score: null`.
2. **Separation from its own floors** (`CLAUDE.md:159-161` — "ask what value it takes when the arm
   does nothing"). Each frame's subject score is quoted beside the same embedder's scores for:
   * **background floor:** the reference vs the same generated frame's region *outside* the
     dilated mask (same frame, same lighting, same codec);
   * **decoy floor:** a *different* canonical character's reference vs the same subject crop;
   * **plate floor:** the reference vs the neutral plate alone.

   A frame is `fired: true` only if its subject score exceeds the **maximum** of its floors. If
   not, it reads `NOT SEPARABLE` with the floors shown and `score: null` — the instrument could
   not tell this character from background or from another character on that frame.

The clip line reads `fired k/n frames`, the median over fired frames only, and the floor maxima
beside it. **The decoy character** must be another canonical asset of the same style family, so
the decoy floor is the hard one; which asset is a premise each run records.

### 3.4 It gates nothing — said plainly, and built so it cannot

**Masked identity gates nothing.** No score, floor or fired count raises, halts, skips, selects a
seed, or chooses an arm. The module defines no `GateFailure` subclass; its only refusals are
input-shape refusals (`gate: None`), as in `clipstats`. A test pins that a catastrophically low
score returns normally (§5, I5). Whether the figure is the same character is the Director's, by
eye, at full size (`CLAUDE.md:191-196`, `:226`).

---

## 4. Licences — read at source today (2026-11-11)

Fetched with `Invoke-WebRequest` from the URLs below; sha256 prefixes of the bytes read are in the
reply. HF metadata read from `https://huggingface.co/api/models/<id>` (the `cardData.license`
field and the repo commit `sha`, which pins the exact variant).

### 4.1 Every model or weight the design names

| item (exact variant) | licence at source today | URL read | commercial | note |
|---|---|---|---|---|
| **OpenCV 5.x** (library; `opencv-python-headless` 5.0.0.93 in CI, `opencv-contrib-python` 5.0.0.93 on the rig, `pyproject.toml:125-137`) | Apache-2.0 (core and contrib); wheel scripts MIT; **all wheels ship FFmpeg LGPL-2.1** | raw.githubusercontent.com/opencv/opencv/5.x/LICENSE · …/opencv_contrib/5.x/LICENSE · …/opencv-python/4.x/README.md | **YES** | Tier A's only dependency. **Already a declared runtime dependency with no row in the map** — a gap this design surfaces (§8). FFmpeg LGPL binds redistribution of the wheel, not use. |
| **MapAnything — Apache variant** `facebook/map-anything-apache` @ `00f9c245` (also `…-apache-v1` @ `59bcb2c4`) | `apache-2.0` (HF card); code Apache-2.0 | huggingface.co/api/models/facebook/map-anything-apache · raw…/facebookresearch/map-anything/main/LICENSE | **YES** | README: two variants "with different licensing based on the underlying training datasets"; "For Commercial Use: Use `facebook/map-anything-apache`". Tier B candidate. |
| MapAnything — default `facebook/map-anything` @ `a1d87e90` | `cc-by-nc-4.0` | huggingface.co/api/models/facebook/map-anything | **NO — BANNED** | **same filename (`model.safetensors`) as the Apache variant** — see §4.3. |
| VGGT-1B `facebook/VGGT-1B` @ `860abec7` | `cc-by-nc-4.0` (HF card) | huggingface.co/facebook/VGGT-1B/raw/main/README.md | **NO — BANNED** | README: "the original checkpoint remains non-commercial". Files `model.pt`, `model.safetensors`. |
| VGGT-1B-Commercial `facebook/VGGT-1B-Commercial` @ `ebb29a53` | `other` / `vggt-aup-license`; the repo's own `LICENSE` file **returned 401** (gated, manual approval) | huggingface.co/api/models/facebook/VGGT-1B-Commercial · raw…/facebookresearch/vggt/main/LICENSE.txt ("VGGT License v1, July 29, 2025") | **UNVERIFIED → NO** for the exact file; the GitHub VGGT License it points to reads **CONDITIONAL** | The GitHub licence grants use without an NC clause but carries an Acceptable Use Policy (military/ITAR, among others), lets Meta "modify this Agreement from time to time… effective immediately" (§8), and access needs a gated application sharing personal data. The checkpoint's own LICENSE could not be retrieved without accepting the gate — a Director decision, not an executor's. Files: `model.safetensors`, `vggt_1B_commercial.pt`. |
| VGGT-Omega `facebook/VGGT-Omega` | `other` / `fair-noncommercial-research-license`, gated | huggingface.co/api/models/facebook/VGGT-Omega | **NO — BANNED** | released 2026-05-18 per the VGGT README. |
| MonST3R `Junyi42/MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt` @ `1ea2a9ea` | `cc-by-nc-sa-4.0` (HF); repo LICENSE CC BY-NC-SA 4.0 | raw…/Junyi42/monst3r/main/LICENSE | **NO — BANNED** | fine-tuned from DUSt3R. |
| DUSt3R `naver/DUSt3R_ViTLarge_BaseDecoder_512_dpt` @ `61c57447` | repo LICENSE: CC BY-NC-SA 4.0 (HF card declares none) | raw…/naver/dust3r/main/LICENSE | **NO — BANNED** | — |
| MASt3R `naver/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric` @ `06e7259f` | repo LICENSE: CC BY-NC-SA 4.0 (HF card declares none) | raw…/naver/mast3r/main/LICENSE | **NO — BANNED** | — |
| CUT3R (any other named in the field) | repo LICENSE: CC BY-NC-SA 4.0 | raw…/CUT3R/CUT3R/main/LICENSE | **NO — BANNED** | — |
| π³ `yyfz233/Pi3` @ `ae722e70` | `bsd-2-clause` (HF); repo LICENSE BSD | huggingface.co/api/models/yyfz233/Pi3 · raw…/yyfz/Pi3/main/LICENSE | **CONDITIONAL** (residual) | Clean on its face. Residual: its training-data composition was **not checked** today, and MapAnything's own README treats training data as what decides a weight's licence; the map already records a data licence reaching through weights (AMASS, `docs/license-map.md:167`). Not proposed; listed so nobody adopts it on the badge. |
| **DINOv2** `facebook/dinov2-small` @ `ed25f3a3`, `-base` @ `f9e44c81`, `-large` @ `47b73eef`, `-giant` @ `611a9d42`, `-with-registers-base` @ `a1d738cc` | `apache-2.0` (each HF card); repo LICENSE Apache-2.0 | huggingface.co/api/models/facebook/dinov2-* · raw…/facebookresearch/dinov2/main/LICENSE | **YES** | primary masked-identity embedder: **`dinov2-base`**, file `model.safetensors`. |
| DINOv3 `facebook/dinov3-vitb16-pretrain-lvd1689m` | `other` / DINOv3 License (custom, gated manual) | raw…/facebookresearch/dinov3/main/LICENSE.md | **CONDITIONAL** | not needed; DINOv2 is Apache. |
| DINO v1 (DreamSim's `dino_vitb16` backbone) | Apache-2.0 | raw…/facebookresearch/dino/main/LICENSE | **YES** | only if a DreamSim variant built on it is ever ruled in. |
| DreamSim (code) | MIT | raw…/ssundaram21/dreamsim/main/LICENSE | **YES (code)** | — |
| DreamSim (weights: `dreamsim_dinov2_vitb14_checkpoint.zip`, 323,484,148 bytes, GitHub release `v0.2.1-checkpoints`; others in `v0.2.0`) | **no licence statement on the release** ("Checkpoints for v0.2.1 release.") | api.github.com/repos/ssundaram21/dreamsim/releases/tags/v0.2.1-checkpoints · …/dreamsim/config.py | **UNVERIFIED → NO** until ruled | Whether the repo MIT covers its release assets is the same shape as the map's DWPose and rembg weight traps (`docs/license-map.md:117`, `:125`). Fine-tune data NIGHTS is SD-2.1-generated and its README states no licence. R&D/Director ruling. |
| CLIP (OpenAI) `openai/clip-vit-base-patch32` @ `3d74acf9`, `-large-patch14` @ `32bd6428` | repo LICENSE MIT; HF cards declare no licence and say "**Any** deployed use case of the model - whether commercial or not - is currently out of scope" | raw…/openai/CLIP/main/LICENSE · huggingface.co/openai/clip-vit-base-patch32/raw/main/README.md | **YES by MIT; not used** | intended-use statement, not a licence clause — the map's laion precedent (`docs/license-map.md:69`). Not used: DINO is the recorded lead. |
| OpenCLIP (code) | MIT | raw…/mlfoundations/open_clip/main/LICENSE | YES (code) | only via DreamSim ensembles; not proposed. |
| InsightFace / ArcFace models | code MIT; "training data… (and the models trained with these data) are available for non-commercial research purposes only" | raw…/deepinsight/insightface/master/README.md | **NO — BANNED** | the face-embedding tier the law warns about; out by licence as well as by `CLAUDE.md:198-200`. |
| SAM 2.1 `facebook/sam2.1-hiera-large` @ `665f8e2a` | `apache-2.0`; repo LICENSE Apache-2.0 | raw…/facebookresearch/sam2/main/LICENSE | **YES** (re-fetched) | map row dated 2026-08-10 is **advisory since 2026-11-08**; today's fetch reads the same. Only for later placement evidence. |
| BiRefNet `ZhengPeng7/BiRefNet` @ `e2bf8e44` | `mit`; repo LICENSE MIT | raw…/ZhengPeng7/BiRefNet/main/LICENSE | **YES** (re-fetched) | same ageing note. |
| COLMAP / GLOMAP (alternative to Tier A, not proposed) | new BSD (COLMAP: "refers only to the license for COLMAP itself, independent of its dependencies"); GLOMAP BSD-3 | raw…/colmap/colmap/main/LICENSE · raw…/colmap/glomap/main/LICENSE | YES (with dependency caveat) | external binary; OpenCV covers Tier A without it. |

### 4.2 Rows that would need adding

**`docs/license-map.md`** — a new section "Measurement tier — shot diagnostics (fetched
2026-11-11)", each row with name, exact variant (repo id + commit), licence, URL, operative
clause, fetch date and verdict per the map's procedure (`docs/license-map.md:246-253`):

* YES: OpenCV 5.x (+ the wheel's FFmpeg LGPL note); MapAnything-apache; DINOv2 (four sizes +
  registers, one row per variant); DINO v1 (only if DreamSim is ruled in).
* NO — BANNED: MapAnything (default); VGGT-1B; VGGT-Omega; MonST3R; DUSt3R; MASt3R; CUT3R;
  InsightFace models.
* UNVERIFIED → NO, into the UNVERIFIED table: VGGT-1B-Commercial (checkpoint licence behind a
  manual gate); DreamSim weights.
* CONDITIONAL, surfaced to the Director: VGGT-1B-Commercial's family licence (if the gate is ever
  accepted and the file's LICENSE read); π³ (training-data residual); DINOv3.
* Re-dated: SAM 2.1 and BiRefNet rows (advisory since 2026-11-08; re-read today, unchanged).

**`tools/armature_core/route_gates.py`** — see §4.3 for why the existing table cannot carry most
of these, and what is proposed instead.

### 4.3 The mirror, and a trap the current table cannot see

`RULED_COMPONENTS` matches **filename substrings** (`rulings_for`, `route_gates.py:1778-1798`) and
the strictest verdict wins (`VERDICT_RANK`, `:1472-1484`). That works for Comfy graphs, whose
filenames are distinctive. It **cannot** work for this tier, measured from today's HF listings:

* `facebook/map-anything` (BANNED) and `facebook/map-anything-apache` (YES) both ship
  **`model.safetensors`**;
* `facebook/VGGT-1B` (BANNED) ships `model.safetensors`; `facebook/VGGT-1B-Commercial` ships
  `model.safetensors` too;
* a bare `"vggt"` BANNED row would also match `vggt_1B_commercial.pt` and, by rank, refuse it.

So a filename-keyed row is either blind (BANNED file passes as `model.safetensors`) or wrong
(the clean file refused by a family stem). Proposed instead:

1. **`MEASUREMENT_WEIGHTS`**, a new mirror table in `route_gates.py` beside `RULED_COMPONENTS`,
   keyed by **(repo id, commit, filename, sha256)**, each row carrying `verdict`, `licence`,
   `fetched`, `source` — the same fields the existing mirror carries and for the same reason
   (`route_gates.py:78-98`). An unknown key is **refused**, not shrugged: a weight not on the table
   is UNVERIFIED, and UNVERIFIED is NO (`CLAUDE.md:185`).
2. **A load gate inside the tool that loads** (`CLAUDE.md:142-147`): before any weight file is
   opened, the loader hashes it and looks it up; BANNED, UNVERIFIED or unknown raises a
   `GateFailure` subclass (`MeasureWeightGate`, gate id `MEASURE_WEIGHT`), CONDITIONAL raises unless
   the record names the Director's ruling. The receipt carries the ruling's age via the existing
   `licence_fetch_reading` shape (`route_gates.py:1528-1541`).
3. **BANNED rows in `RULED_COMPONENTS` only for distinctive stems** that appear in published
   filenames — `monst3r`, `dust3r`, `mast3r`, `cut3r`, `vggt_omega` — so a Comfy graph naming one
   halts, per the existing practice of entering dead rows so they halt instead of shrugging
   (`route_gates.py:130-133`). **No bare `vggt` row** (it would out-rank the commercial file).

---

## 5. Tests — CPU only, synthetic fixtures, each built to fail when the diagnostic is wrong

No model is loaded by any test. The embedder is an injected interface; tests use deterministic
stand-ins. For each test: what it catches ("what would this look like if the code were wrong in
the specific way this check exists to catch", `CLAUDE.md:138-141`).

**Fixture 1 — geometric (correspondences, no images).** A seeded random 3D point set (two
background planes + a separate "performer" point cluster that moves non-rigidly), projected
through a **known orbit path built with the repo's own `framing.camera_position` /
`camera_basis`** and `K` from `framing.half_fovs(50, 36, 832, 480)`, with optional pixel noise.

**Fixture 2 — image sequence (numpy + cv2 only, small: ~9 frames at 256×144).** A procedural
texture on a ground plane and backdrop, warped per frame by the plane-induced homographies of a
known camera path; a moving coloured blob as the "character" with its exact mask; written as
`NNNNN.png` plus a `manifest.json` in `stage_render`'s per-frame record shape (`camera_matrix`
in Blender convention, `mask_px`, `mask_bbox`). Plus a **deliberately wrong** GT path for the
same frames.

| id | test | fails when |
|---|---|---|
| C1 | correct path, noiseless correspondences → `rot_err_deg` ≈ 0 to float tolerance at every frame | the pose recovery, anchoring or composition order is wrong |
| C2 | same estimate scored against a **static** GT for a 30° orbit → final-frame `rot_err_deg` = 30° ± fixture tolerance; `est/gt span` reads ~1 against the true path and is undefined-safe against static | the diagnostic reports "followed" for a camera that moved differently (the core failure it exists for) |
| C3 | estimate translations multiplied by an arbitrary `k` → direction errors unchanged; fitted `s = 1/k`; ATE ≈ 0 | scale leaks into the scale-free readings, or more than one parameter is fitted |
| C4 | a GT `camera_matrix` fed in Blender convention vs mistakenly already-OpenCV → correct path reads ≈ 0 only with the flip; without it, ≫ 90° | the Blender→OpenCV axis flip is missing or doubled |
| C5 | a global rotation offset applied to the whole estimated trajectory → rotation error unchanged (gauge removed by anchoring); a **per-frame drift** applied → error grows exactly by the drift | the alignment fits away real rotation error (Sim(3) absorption) |
| C6 | pure pan (rotation-only path) → `model: H`, rotation recovered, `tdir_err_deg: null` with reason `t_unobservable` | a direction number is invented where translation is unobservable |
| C7 | correspondences reduced below the solver minimum, or all on the character → `fired: false`, all errors `null`, counts recorded | a number is produced from a solver that did not fire |
| C8 | performer cluster included vs excluded by the mask → error larger when the mask is **not** applied; test asserts the CLI path applies it | the character mask is not wired into feature selection |
| C9 | Fixture 2 end-to-end through SIFT + E/H: correct GT → small error; wrong GT (sweep reversed) → error ≈ the known gap | the image path diverges from the geometric core |
| C10 | Static request with a synthetic push-in → parallax evidence > 0; with a pure hold → ≈ 0 | parallax is not computed on the background inliers or is computed on the character |
| C11 | frame counts differ / aspect differs / no `camera_matrix` → each refuses with its named clause; a different resolution at the same aspect records the `K` scale | an unknowable `K` or GT reaches the metrics |
| C12 | `followed` reads the literal NO-THRESHOLD string; a test pins that no boolean appears in the record | an invented threshold leaks in before calibration |
| I1 | identical character region, background changed → masked score unchanged, whole-frame score changes | the crop/plate is not applied (the background corrupts the score) |
| I2 | identical background, character region changed → masked score drops | the masked score does not depend on the subject |
| I3 | mask below one patch, or subject score ≤ max floor → `fired: false` / `NOT SEPARABLE`, `score: null`, floors shown | a number is quoted from a crop that did not fire |
| I4 | decoy floor computed from a **different** reference than the subject's → test fails if the decoy and subject references are the same object | the decoy floor is trivially low (self-comparison) |
| I5 | a catastrophically low subject score → returns normally, `status` DIAGNOSTIC; the module exposes no `GateFailure` subclass | the identity diagnostic can gate |
| I6 | identity block without camera block → `ShotDiagError` clause `identity_without_camera_block`; with a NOT FIRED camera block → accepted; JSON key order camera-first; sheet lines camera-first | the report shows identity without (or before) camera |
| L1 | load gate: a file whose bytes hash to a BANNED or unknown table key raises `MeasureWeightGate` **even when its filename is `model.safetensors`, identical to an allowed row's** | the gate keys on filename (the trap in §4.3) |
| L2 | `RULED_COMPONENTS` stem rows: `MonST3R_PO-TA-S-W_ViTLarge_BaseDecoder_512_dpt.pth` → BANNED; `vggt_1B_commercial.pt` → **not** BANNED by any stem row | a family stem out-ranks the commercial variant, or a BANNED stem is missing |
| L3 | the load gate refuses before importing any heavy dependency (the test environment has no torch) | the licence decision happens after the weight is loaded |
| M1 | every new `MEASUREMENT_WEIGHTS` row has a dated `fetched` and a `source` URL, or `source: None` on a recorded non-retrieval — the existing mirror's rule | a row a gate cannot age |

Run order after CARD FREE: the new tests, then the full suite, logged (last 15 lines each); then
the new tests at base, pasting the failing lines (they must fail there, or they test nothing).

---

## 6. Cost — on the 5090 (32 GB, `CLAUDE.md:248`) and on CPU

| component | weights (read at source) | VRAM per clip | time per clip | CPU? |
|---|---|---|---|---|
| Tier A, OpenCV SIFT + E/H, 81 frames 832×480 | none | 0 | [Guess] 10–40 s | **yes — CPU-only by design** |
| Tier B, MapAnything-apache, 81 views at 518 px | `…-apache-v1`: 563,336,150 F32 params (HF API) ≈ 2.25 GB F32; current `…-apache` size not read | [Guess] 4–10 GB bf16 (README: memory-efficient mode "up to 2000 views on 140 GB") | [Guess] 2–15 s | [Guess] possible, minutes per clip |
| VGGT-1B-Commercial (excluded) | 1,256,537,516 F32 params (HF API) ≈ 5.0 GB F32 | [Guess] 10–20 GB at 81 frames | [Guess] seconds | [Guess] impractical |
| Masked identity, DINOv2-B/14, 81 crops + 8 refs + floors (~3 extra crops/frame) at 224 px | `dinov2-base` [Guess] ~86 M params (~0.35 GB F32) — size not read today | [Guess] < 1.5 GB | [Guess] < 5 s | [Guess] **yes**, ~0.1–0.3 s per crop → ~1–2 min per clip |
| DreamSim `dinov2_vitb14` (deferred) | checkpoint zip 323,484,148 bytes (GitHub API) | [Guess] < 2 GB | [Guess] < 5 s | [Guess] yes |

Everything in the Part 2 build (Tier A, the identity framework with stand-in embedders, the load
gate) runs on CPU. Any run of a real learned model — DINOv2 included, though it would fit on CPU —
goes through R&D and the Publisher's grant, because it needs a weight download this card forbids.

---

## 7. Premises — measured or assumed

| premise | status |
|---|---|
| `stage_render` writes per-frame `camera_matrix` (cam→world, Blender convention) and a `mask/` channel | **measured** by reading `stage_render.py:290`, `:387`, `:397-409` |
| Intrinsics follow Blender AUTO fit as `framing.half_fovs` computes | **measured** by reading `framing.py:152-207` (pinned to `blender_scene` by `tests/test_framing.py`, per its docstring) |
| No other renderer records per-frame camera matrices | **measured** by search in `render_performer.py`, `preview_walk.py`, `render_start_frame.py`, `preview_glb.py` |
| The generated clip's frames correspond 1:1 in time to the rendered frames | **assumed** — refused unless counts match or a map is given |
| The generator kept the requested focal length | **assumed** — Tier A holds `K` fixed; a zooming model biases rotation. Tier B can report its own recovered intrinsics as a check |
| OpenCV's SIFT is in the installed `cv2` 5.0 builds | **assumed** (true since 4.4 upstream; not run on the rig — no Python allowed) |
| MapAnything-apache runs without pulling a non-Apache weight at runtime | **assumed** — must be measured at its first grant run by listing every file opened (`CLAUDE.md:283-288`) |
| The HF repo commit shas in §4.1 are the variants that would be loaded | **measured** today from the HF API; pins go into `MEASUREMENT_WEIGHTS` |
| A decoy canonical character of the same style family exists for each shot | **assumed** — each run names it |

---

## 8. Findings while reading (not changed; listed)

1. **OpenCV has no licence-map row** although it is a declared runtime dependency
   (`pyproject.toml:139-144`) and the rig runs a different distribution of it
   (`pyproject.toml:125-137`). Today's fetch reads Apache-2.0 (+ FFmpeg LGPL-2.1 inside every
   wheel). Proposed as a row in §4.2.
2. **`render_performer --camera-path` appears to render a static camera.** The path is solved for
   framing (`render_performer.py:619-638`), but the camera is placed once from the module constants
   `ELEVATION_DEG, AZIMUTH_DEG` (`:717-718`) and the frame loop (`:724-749`) never moves it; the
   provenance records both the path (`:829`) and the static camera (`:844-856`). `preview_walk`
   does re-sample per frame (`preview_walk.py:412-429`). Read, not run. Consequence here: GT is
   taken only from per-frame recorded matrices, never from a path file.
3. **`stage_render` places the camera by orbit only** (`stage_render.py:263-267`) and has no read
   of `camera.keys`, while `shotspec` accepts `path` / `track` types with keys
   (`shotspec.py:563-587`). Read, not run. A path shot therefore has no per-frame GT record today;
   adding one to a renderer is outside this card unless ruled (D5).
4. **Every existing `RULED_COMPONENTS` row is advisory or goes advisory today**: the 2026-08-10
   rows on 2026-11-08 and the 2026-08-13 rows on 2026-11-11 — the module's own header names those
   dates (`route_gates.py:83-85`). The 2026-08-10 map rows (`docs/license-map.md:26`) are likewise
   past 90 days.
5. `WEIGHT_SUFFIXES` (`route_gates.py:464`) has no `.bin`; HF repos still ship
   `pytorch_model.bin` (DINOv2, CLIP listings today). Irrelevant to Comfy graphs today; noted
   because §4.3's table keys on hashes, not suffixes.

---

## 9. Out of scope — listed, not changed

PR #26's files; the Pillow fix (#24); any route payload builder; releases; checklist scoring
(the lead that checklist questions agree with people better than 1-to-5 grades is recorded and
not built). Also not touched: `E:/AI/armature`, and the worktrees
`armature-preproc-licence`, `armature-ci24`, `armature-pr26-review2`. This branch is a fresh
clone at `E:/AI/_worktrees/armature-shot-diagnostics`.

---

## 10. Decisions for R&D

| id | decision | this design's recommendation |
|---|---|---|
| **D1** | camera error: hard check or diagnostic | **diagnostic** now (§2.6); gate only after calibration, before a named irreversible step, by ruling |
| D2 | Part 2 camera tier | build **Tier A (OpenCV)** only; Tier B (MapAnything-apache) as a later grant run against Tier A |
| D3 | Part 2 identity scope | build the masked-identity framework (crops, floors, fired evidence, record, refusals) with an injected embedder and stand-in tests; write the DINOv2 adapter behind the load gate but **load nothing** until a grant run |
| D4 | licence rows | add the §4.2 rows to the map and the §4.3 `MEASUREMENT_WEIGHTS` table + stem rows to `route_gates`; DreamSim weights and VGGT-1B-Commercial into UNVERIFIED |
| D5 | per-frame camera records for path shots (finding 3) and the `render_performer` camera (finding 2) | out of this card unless ruled; the diagnostic refuses without GT |
| D6 | CONDITIONALs for the Director | VGGT-1B-Commercial (gate + AUP + unilateral modification), π³ (training data), DINOv3 — none needed by this design |

---

## 11. Proposed Part 2 file list (if ruled as recommended)

* `tools/armature_core/shotdiag.py` — core (§2, §3).
* `tools/measure_shot.py` — CLI.
* `tools/armature_core/route_gates.py` — `MEASUREMENT_WEIGHTS`, `MeasureWeightGate`, five stem rows.
* `tools/sheet_compose.py` — `measure_shot` branch in `diagnostic_lines`, camera lines first.
* `tests/test_shotdiag_camera.py`, `tests/test_shotdiag_identity.py`,
  `tests/test_measure_weight_gate.py` — §5; fixtures generated in-test (numpy + cv2), nothing
  binary committed.
* `docs/license-map.md` — §4.2 rows; `docs/tools.md` — one row; `CHANGELOG.md` `[Unreleased]`.
* Atlas regenerated with the repo pin (`npx --yes @dogfood-lab/atlas@1.24.0`, `ci.yml:465-467`)
  after CARD FREE only — this design file itself adds a doc the committed Atlas does not list yet.

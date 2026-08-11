# Comfy consult #3 — findings, calibrated 2026-08-10

Consult brief: prose-only, no build order, nothing fetched into a tab. Answers relayed by the
Director. **This document records what was verified, what is credible-but-unverified, and what
the channel explicitly refused to guess.**

## Calibration — PASSED, and this is why the rest is weighted credible

Standing practice: verify one cheap independently-checkable claim before acting on expensive ones.
The consult declared `WanVaceToVideo`'s complete socket list. Checked against our own submitted
payload (`outputs/E02/payloads/A1b.json`):

| declared | ours |
|---|---|
| required: `positive` `negative` `vae` `width` `height` `length` `batch_size` `strength` | **all 8 present, exact** |
| optional: `control_video` (IMAGE), `reference_image` (IMAGE) | **both present, exact** |
| optional: `control_masks` (MASK, **plural**) | **absent — we have never wired it.** Name not independently confirmable from our payload |
| frame count 4n+1 | **33 = 4·8+1 ✓** |
| width/height multiples of 16 | **480/16 = 30 ✓, 832/16 = 52 ✓** |

Ten of ten socket names we can check match exactly. **Also confirmed while checking: our payload
contains no LoRA loader of any kind**, so the CausVid non-commercial trap has never been present
in an armature submission.

The channel was explicit about its own gaps — it declined to invent a native max frame count, a
max resolution, or a mechanism for the PNG-bridge decrement. That refusal is part of why the rest
is credible.

## ⭐ The finding with the most leverage: `control_masks`

**VACE accepts a per-frame mask defining where the control signal applies.** Where the mask is
active the model is bound by control; where it is inactive the model is free.

**armature has the exact subject silhouette every frame, for free, from geometry** — no estimator,
no licence exposure. That means we can say: *obey the depth control on the character, invent
everything else.* A model-painted world around a control-locked character.

Contract, to be verified empirically before anything is built on it:

* type `MASK`, single channel, float **1.0 = active, 0.0 = free** — so subject silhouette white.
  **Verify polarity on a one-frame test; if control leaks into the background, invert.**
* **per-frame**, a sequence matching `length` — a single static mask would be wrong for a moving
  character. Padded/truncated to `length` the same way `control_video` is.
* values in [0,1] — probe that an 8-bit matte arrives as 0/1 and not 0/255.

This is the highest-value under-used input in our stack and it is a candidate experiment.

## Length — 33 frames is well under the trained horizon

* The ceiling is **soft and governed by the training distribution**, not a hard cap. Wan 2.1 VACE
  14B was trained around the **81-frame class (~5 s at 16 fps)** at 480p/720p. The node accepts
  more; coherence and identity degrade past the trained horizon.
* **VRAM is the hard wall** on Cloud and is a stop, not a degradation.
* **81 frames (4·20+1) is the cheapest available win** — one widget value. We run 33 (~1.4 s).
* The consult **declined to state an exact native max** or a max resolution. Unknown, not assumed.

⚠ **A floor measured at 33 frames is not automatically the floor at 81.** Length changes the
population; see E04's scope note.

## Chaining — the architectural finding for a video tool

**Control does NOT carry across a chained seam.** VACE consumes a `control_video` of exactly
`length` for the clip it is generating and has no memory of a previous chunk.

**For armature this is the clean case**, because we author the control for the whole shot in
Blender: we slice our own depth sequence per chunk (with a frame of overlap at the seam) and hand
each chunk its own byte-exact slice. **The geometry does not drift across a seam — only what the
model invents does.**

**And the load-bearing rule:** re-anchor every chunk to the **one canonical reference image**,
never to the previous chunk's output. Anchoring to the previous output **compounds** drift;
anchoring every chunk to one reference is what keeps the man the same man.

## Control scheduling — the lever does not exist for video

Our best image-side win was the depth schedule (0.80 / 0.0 / 0.45, release control early).
**There is no video analogue and it cannot currently be tested.**

* `WanVaceToVideo` exposes only a scalar `strength`. No start/end percent, no per-frame weighting.
* **Neither** `WanFunControlToVideo` **nor** `Wan22FunControlToVideo` exposes a schedule either.
* Community nodes hinting at richer strength control (`WanVaceAdvanced` tier) are
  **licence-unverified — treated as NO**.

**Mechanism, and the consult was careful to mark it as reasoning rather than fact:** the image
insight is *per-frame*. Releasing control mid-denoise also removes the anchor keeping successive
frames consistent with each other, which has no still-image analogue and would read as **temporal
drift/shimmer**. Its honest position: *it does not know that it transfers, has a mechanism reason
to expect it does not, and the tool to measure it is not on the licence-clean list.*

**Ruled: `strength` stays 1.0 on VACE.** Any scheduling experiment is gated on first finding a
schedulable, licence-clean node.

## Wan 2.2 Animate — a native continuation contract, but the wrong input shape for us today

`WanAnimateToVideo` factors conditioning that VACE fuses: `reference_image` (who), `pose_video`
(body), `face_video` (face), `background_video`, `character_mask` (where), plus
**`continue_motion` / `continue_motion_max_frames` / `video_frame_offset`** — a purpose-built
chunk-continuation contract, which is exactly the long-form mechanism VACE lacks.

**But it wants a pose skeleton, not depth.** Our control is a geometry-rendered depth pass. We
would have to emit Animate's expected pose representation from Blender — which we *can* do, since
we own the bone transforms, and doing so sidesteps the detector tier entirely.

**Read: VACE for single clips up to the trained horizon; evaluate Animate specifically for the
chaining problem**, and only after confirming we can author its pose input without touching a
non-commercial detector.

## Identity — mechanism only, outcome to be measured here

* `reference_image` is an IMAGE socket and IMAGE is a batch tensor, so it accepts a **stack**.
  Extra references are **appearance anchors**, not per-frame identity control. A small consistent
  stack of the same man from several angles is more robust than one frontal still — it gives
  appearance evidence for profile and back, which matters exactly when our armature turns him.
* **Character LoRA binds identity into the weights**, reasserting it every frame and every clip
  regardless of reference; a reference stack carries identity per generation and can still drift.
  Suggested combination: LoRA trained on our canonical mesh renders **plus** a small reference
  stack at inference.
* ⭐ **A LoRA trained on our own canonical mesh renders is licence-clean by construction.** That is
  a real structural advantage of this pipeline and worth protecting.

**All of this is mechanism. What actually happens to identity gets measured here, not asked.**

## Licence flags raised — all treated as NO until retrieved

| item | status |
|---|---|
| `FL_WanVaceToVideoMultiRef` / Fill custom-node pack | **UNVERIFIED → NO** |
| `WanVaceAdvanced` tier (`VaceStrengthTester`, `VaceAdvancedModelPatch`) | **UNVERIFIED → NO** |
| `WanAnimatePreprocess` detector tier (ViTPose / DWPose weights) | **UNVERIFIED → NO** — and it forced a correction to our own map, below |
| `Wan2.2-VACE-Fun-A14B` **Cloud node availability** | **UNCONFIRMED** — the weight name is on our licence map, but the consult found no node by that name; the 2.2 control route presents as Fun-Control and Animate |

### ⚑ A correction to our own licence map, earned by this consult

Our DWPose row read **Apache 2.0 → YES**, citing
`raw.githubusercontent.com/IDEA-Research/DWPose/onnx/LICENSE`. **That document is the code
licence.** The consult flagged the detector *weights* tier as a non-commercial minefield, and it
is right that the two are separable — **this is the identical trap our own map already records for
`rembg`** ("MIT covers code only — bundled weights carry separate licenses, not yet fetched").

**The row is narrowed:** DWPose **code** is Apache; DWPose **weights** are **NOT FETCHED, therefore
UNVERIFIED, therefore NO.** Nothing in armature depends on it — we render pose from geometry — so
this costs us nothing and closes a hole that would have opened the moment someone reached for a
pose preprocessor.

## Platform behaviours we reported back

* **Determinism at fixed seed** — consistent with the schema; nondeterminism lives in the encoder,
  not the sampler. Our H.264 conclusion is endorsed, not independently re-measured.
* **`dry_run` PASS then submit refusal** — structurally expected: a schema/enum validator can pass
  a graph whose *link topology* is still illegal at execution. Our practice of checking topology in
  code and refusing to cite `dry_run` as evidence of runnability stands.
* **PNG-batch `max(src−1,0)`** — the consult **does not know** the cause and declined to guess. Its
  general remedy: **fewer encode/decode hops** between Blender and `control_video` — hand VACE a
  single IMAGE batch without a per-image round-trip, rather than a PNG re-encode per frame.

## What this opens — candidates, not yet specified

Named here so they are not lost, and deliberately not specced while E03 is mid-flight:

1. **`control_masks` + geometry silhouette** — control-locked character, model-invented world.
2. **81 frames** — one widget value, ~5 s, inside the trained horizon.
3. **Chained clips at one canonical reference** — the long-form performance test.
4. **The Blender→`control_video` hop count** — whether a lower-hop path removes the −1.

Related: [[E04-the-between-generation-floor]] · `docs/license-map.md`

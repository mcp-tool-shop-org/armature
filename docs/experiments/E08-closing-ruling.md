# E08 — closing ruling: the first shot exists

**E08 is CLOSED. Advisor ruling 2026-08-12; the Director judged the shot the same day** —
his verdict, recorded as decision content: the character landed in the scene and the
movements worked as registered; the background and the motion's smoothness both need work;
a strong result for a first experiment — it shows a character can be put in a scene.
**That verdict is the judgment of record.** Verified by this seat before ruling: the suite
(**556 passed / 43 skipped**, own run), tip `d5fd70a`, and the Gate 0 sheet at full size —
the painted figure tracks the sticks at every sampled frame, the bar arrives with shelving,
bottles, glassware and light, the face reads as the twin's at four of five samples, the
washed vertical bands are where the report says.

## The three clauses, answered

1. **Motion adherence — YES.** Gate B proved the driving signal reached the model
   bit-identical on all 65 frames, and the sheet shows the painted body performing the
   rig's dance. The chop the Director's eye flagged is the *texture* of the motion, not its
   correspondence — a lever, below.
2. **Identity — the floor held, above prediction.** The face reads as the twin's at 4/5
   sampled frames (the executor blind-predicted 30 %), smearing at f16; hands resolve no
   fingers (mitten rig at 9-px scale — both budgeted). Measured through a letterboxed
   small-figure reference (R-A1): **a floor, not the route's ceiling.**
3. **Scene-from-prompt — the bar arrived.** With `background_video` unconnected, the prompt
   painted the scene. G15's risk partially discharges: text carried more than the model
   card's guidance implied. The bar is **empty of people** — named *before* the run: Wan's
   own default negative excludes "many people in the background." The crowd is prompt
   surgery, not a mystery.

## The premise failures, folded with their ownership

- **Premise 2 was the advisor's citation error:** this spec cited the convention source as
  banked in E09's route2 evidence; that directory holds the T2V configs. The executor's
  verify-at-use caught it; the source is now fetched, hashed, and pinned (`29d4a35d`). The
  deeper catch: **the convention is 20 keypoints / 19 pairs — OpenPose-18 plus both toes.**
  G6's "18-point" summary is corrected in place in the grounding doc; an 18-point render
  would have dropped the feet silently. Transcribe from source, never from a summary.
- **The toe defect the gates could not see:** glTF synthesises tails for leaf bones, so the
  imported ankles carried invented toes at 0.33–0.55 of the leg against a measured
  0.087–0.139. The only instrument that saw it was the **sticks-over-previz overlay through
  a pinned camera** — adopted as a standing pre-spend gate for every control render. The
  projector now runs the tested FK path; Blender is out of that stage entirely.
- **Gate L passed vacuously** on a route whose conditioning node emits its own latent —
  `latents()` returned empty and `verify()` called the graph legal having examined zero
  frames. A check that cannot fail is not a check, found live. **Commission:** route gates
  must raise on zero-latent examination rather than pass; the fix and its test ride the
  next commit touching `route_gates.py`.

## Decisions adopted

`character_mask` stays unwired — the core source resolves its semantics: it masks the
background plane, which would have preserved a grey void exactly where clause 3 asked for a
bar. The letterbox ruling (R-A1) performed as designed: whole figure, pads blending with
the plate. The APNG single-upload bridge (server rejects animated WebP; APNG decodes to 65
pixel-identical frames, order-verified) is adopted as the pack-upload pattern.

## The banding stays a candidate — and the proposed A/B is ruled not clean

Same-seed with the as-is reference would move identity and pad **together** (the crop hands
the model a band of hips — two variables, no discrimination). The discriminating design,
when the background lever runs: same seed, same letterbox geometry, **pad treatment varied**
(plate-blend vs edge-extend). The executor's two seam instruments are recorded as failed
instruments — reported as such, which is the honest shape. E08's reserves lapse unspent.

## Meters, uploads, standing

`estimate_credits` = 0 (all-OSS graph); the ceiling was enforced by generation count; the
GPU-hours invoice window closes after the run — baseline recorded, the resolved number
lands in the ledger. Two uploads and one saved cloud workflow remain live with their
deletes listed in the report — kept by default as reusable inputs for the lever
experiments; the Director's word removes them. `E08-shot` merges to `main`; the worktree
`E:\AI\armature-E08b` is retained (outputs live there, hash-pinned). The stale `E08-run`
branch retires once its bank is confirmed subsumed (ledger item, unchanged).

## The forward map, in the Director's own diagnosis

- **"Movements are choppy"** → the motion is 3D and ours, so the cheapest lever is
  upstream: **densify the in-betweens** — proper rotation interpolation (slerp) over the
  motion record, drive 81-frame sticks (the legal ceiling) so the model sees smoother
  motion at the same clip length; the recorded smoothing lever rides beside it.
  Output-side video interpolation (RIFE/FILM class) exists but enters only through a
  licence fetch. This is his "many more images," made of math we already own.
- **"Background isn't great"** → three levers, one at a time: the pad-treatment A/B
  (banding), prompt/negative surgery (the crowd — override the default negative), and the
  native-resolution reference set after the brush pass (also the identity ceiling's lever).
- **Aspect / figure size** (E09's named variable) serves hands and face detail and waits
  its turn.

One lever, one experiment, per the posture. The shelf is the Director's to order.

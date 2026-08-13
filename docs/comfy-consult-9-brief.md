# Comfy Agent consult #9 — brief: the driven route's unpark surface (Animate2 under authored motion)

**From:** the armature advisor seat, 2026-08-13 · **Relay:** the Director carries this
brief to the Comfy Agent and returns its answer · **Trigger:** the Director's direction
(2026-08-13) to prepare the ground for a **future, unscheduled experiment** — the
skeletal/driven route unparked with movement-library motion. No experiment is dispatched
by this brief; it retrieves the implementation facts the spec will need, on the standing
new-conditioning-tier trigger. · **Numbering:** file series (01, 3, 5, 6, 7, 8 → 9).

**Round shape: knowledge only.** No tabs, no graph building, no generations, no credits
this round. Catalog facts and licence **documents** only — never licence verdicts; the
ruling is ours. UNVERIFIED = NO stands. **Please give all model ids, node names and
filenames as plain text, not code spans** — round 8's relay mangled code-span literals
into "the model" or empty strings.

---

## Context — the experiment this feeds

The driven route (rig-rendered pose sticks → Animate) is parked for AI-animation
buildout. The unpark's intended shape, so the questions land in context:

1. **Motion** comes from a movement library — licence-clean clips (100STYLE-class BVH
   under CC-BY-4.0 survey-grade terms; Mixamo-class usable baked-only) — retargeted in
   Blender onto the studio's own approved skeleton. Survey:
   `docs/research-grounding-movement-library.md`, 2026-08-12.
2. **Pose control is rendered from bone transforms** — no detector anywhere (the
   licence gate: the DWPose/ViTPose weights tier is UNVERIFIED = NO; the served Animate
   template's DWPreprocessor path is not runnable here, measured 2026-08-11).
3. **The paint tier is native Wan-Animate2** (runtime v0.31.0), driving an authored
   reference of the canonical character with the retargeted performance.

Questions are implementation-shaped: what the spec must pin before it can be written.

## Already measured — calibrate against this, do not re-derive

| item | state |
|---|---|
| `WanAnimate2ToVideo` full contract: optional `reference_image` ("the character to animate"), `pose_video`, `continue_motion` (temporal chaining), `positive_pose` (separate motion prompt), CLIP-vision hooks; defaults 832×480×81; tooltips — pose_strength 1.0 = trained behavior, pose_end_percent ≈0.7 keeps choreography while loosening fine detail, reference_image_strength >1.0 tightens identity | **MEASURED** — our `get_node`, 2026-08-12 (consult #8 ruling; field-level truth on dynamic-combo nodes is ours to measure) |
| `WanAnimate2Cache`: MODEL→MODEL pose-branch cache, cpu/gpu, int8/int4 | agent-reported, consult #8 |
| Template `video_wan_animate2` exists; the Animate-2 diffusion checkpoint is chosen at an **upstream loader — exact filename NOT VISIBLE** at consult #8; licence treated NO until identified | consult #8 ruling; the licence map's Animate-2 row |
| The served Animate v1 template (`video_wan2_2_14B_animate`) wires two DWPreprocessor nodes + a SAM2 mask path — reference only, never a route | measured 2026-08-11 |
| The Wan2.2 repo's pose drawing convention (palette, limbSeq, stickwidth formula, separate hand pass) is Apache-2.0 source (`human_visualization.py`) | the licence map, fetched 2026-08-11 |
| Wan-Animate (v1) weights `Wan2.2-Animate-14B` are Apache-2.0 | the licence map (KB row, 2026-08-10) |

## The questions, ranked

**Q0 — calibration (answer first, briefly).** Confirm `WanAnimate2ToVideo` still serves
the contract in the table above (reference_image, pose_video, continue_motion,
positive_pose; defaults 832×480×81). One line if you see no drift; name exactly what
moved if you do.

**Q1 — the loader inventory (the load-bearing question).** Open the template
`video_wan_animate2` and list **every loader node and the exact filename strings it
references** — diffusion checkpoint(s), VAE, text encoder, any pose-branch or CLIP-vision
weights, and the `WanAnimate2Cache` configuration if the template carries one. Plain
text, exact strings as saved. This is what unblocks the licence rows: the Animate-2
weights are treated NO until their documents are fetched, and the documents cannot be
fetched until the filenames are known.

**Q2 — the pose_video contract.** What does the pose branch expect as input?
Specifically: (a) does Animate2 consume the same rendered-stick drawing convention as
Animate v1 (the Wan2.2 repo convention), or a different/updated one — and where is that
documented; (b) resolution / fps / length constraints on `pose_video` relative to the
832×480×81 defaults; (c) the exact node chain between the template's pose input and the
conditioning node — named node by named node — so we can see whether the pose branch is
separable from any detector stage (our pose arrives already rendered from bone
transforms; no detector may enter this pipeline).

**Q3 — chaining.** `continue_motion`'s documented mechanics: per-segment length limits,
overlap or handoff behavior at the seam, whether `positive_pose` and `reference_image`
persist across chained segments, and any documented cap on total chained length.

**Q4 — root translation.** Is there any platform-documented statement on whether the
pose branch carries **root/hip translation** — a character traversing the frame — versus
in-place motion only? If nothing is documented, say NOT VISIBLE; we will measure it
(hip translation is a retargeter setting on our side, read from provenance).

**Q5 — the dated field check.** Since 2026-08-12 (runtime v0.32.0 was current):
anything newly served for skeleton-driven character performance — nodes or templates —
and can Uni3C's camera control compose with Animate2 in any served graph shape
(MODEL-patch chain compatibility)? Names only, as served; no speculation about what
"should" compose.

## Halt conditions

Answer what the catalog and visible documents support; mark everything else NOT
VISIBLE. No speculation, no substitutions of "equivalent" models, no licence verdicts,
no builds. If a question would require building or running anything, stop at naming
what it would take.

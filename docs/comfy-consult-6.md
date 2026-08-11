# Comfy Agent consult #6 — the answer, calibrated and ruled

**Advisor ruling, 2026-08-11.** Brief: [comfy-consult-6-brief.md](comfy-consult-6-brief.md).
The Director relayed the round; the answer arrived with its deviations declared at the top
(no licence retrieval, no cost oracle, OSS names as SPECULATION) — the honest shape the brief
asked for. Per the channel's standing mandate, calibration ran before any finding was
trusted, and this round it earned its keep twice.

## Calibration — measured before any finding was trusted

| # | the agent's claim | our measurement (2026-08-11, zero spend) | verdict |
|---|---|---|---|
| 1 | Q0: `video_wan2_2_14B_animate` and `video_wan_animate2` are both served; the first conditions through `WanAnimateToVideo` | matches our own pre-brief catalog look exactly | **PASS** |
| 2 | Q0/Q3: "Wan Animate 2" conditions through a distinct served core class **`WanAnimate2ToVideo`**, with a stated schema (pose_strength, pose_start/end_percent, reference_image_strength…) | `get_node` by exact class: **missing**. `search_nodes` "WanAnimate": 9 results, none Animate-2. The template's top level shows only subgraph blueprints (UUID-typed) around a plain `LoadVideo` titled "Pose Video" | **FAIL — class unresolved; the claimed schema is unverifiable and is treated as noise** |
| 3 | Closing calibration claim: the served `video_wan2_2_14B_animate` graph feeds `pose_video` from a plain image loader, with **no detector-pack node inline** | the served template's own node list carries **`DWPreprocessor` ×2**, `DownloadAndLoadSAM2Model` + `Sam2Segmentation` + `PointsEditor`, and a `LoadVideo` driving ingest — the detector tier is wired in, at top level | **FAIL — and the agent pre-registered the consequence itself: its graph-level verdicts are to be rechecked before anything builds on them** |
| 4 | The input schemas for `WanAnimateToVideo` and `Wan22FunControlToVideo` (which inputs required vs optional, socket types, continuation sockets) | `get_node` full detail confirms every socket: Animate's six optionals (`reference_image` · `face_video` · `pose_video` · `background_video` · `character_mask` · `continue_motion`, IMAGE/MASK), required `continue_motion_max_frames` + `video_frame_offset` (whose served tooltip reads "Used for generating longer videos by chunk… for extending a video"), defaults literally 832×480; Fun-Control's optional `ref_image` + `control_video` | **PASS — socket-for-socket** |

**Channel verdict this round:** schema-level claims were reliable and are adopted where we
re-verified them; graph-level claims and node-existence claims required our own measurement
and one of each failed. That matches the channel's recorded profile — strong on what-exists
inventory, weak where it must reason past its own tools — and is why calibration is
mandatory, not ceremonial.

## Rulings

**R1 — SLOT 2 route, adopted provisionally: core `WanAnimateToVideo` in a graph we build.**
The served template is **not runnable under the licence gate** — it wires `DWPreprocessor`
(the DWPose-weights tier, UNVERIFIED = NO) at top level. The clean route is the schema truth
we verified ourselves: our own graph (the E02 method — saved workflow file submitted
verbatim, link topology checked in code, no trust in `dry_run`), with `pose_video` fed by
frames rendered from our own rig, `reference_image` from GLB renders, `background_video`
left unconnected so the prompt paints the bar, `character_mask` available to fence identity,
at the already-legal 832×480×65. Licence state: the Wan2.2-Animate-14B weights row was
already Apache in the map; the node-code row is **resolved this round** — ComfyUI core is
GPL-3.0, fetched, with the same narrow output clause as the Blender row (filed under
Services and tools). Provisional means: the Director confirms the route at spec time before
any submission.

**R2 — `Wan22FunControlToVideo` stands as the fallback.** Schema verified, weights Apache,
closest to the saved VACE method. Less identity machinery than R1 (no mask, no face/reference
separation) and expected to hug the control layout.

**R3 — "Wan Animate 2" is demoted to unresolved, not a candidate.** The template exists and
its top level is the cleanest shape seen this round (a plain pose-video loader, no top-level
detector — consistent with its no-pose-extraction description), but the conditioning class
does not resolve in the node catalog, the core hides inside subgraph blueprints, and the
model's weight files and licence are unidentified. It enters through its own round — class,
weights, LICENSE — or not at all. Its claimed strength/scheduling schema is noise until then.

**R4 — SCAIL-2 is NO under the gate**, weights/repo/licence unlocated, and the consult's own
speculation (background inherited from the driving video) points away from the shot's
scene-from-prompt clause. Deprioritized; a row lands in the UNVERIFIED table.

**R5 — SLOT 1 is confirmed unfilled on Comfy Cloud.** The agent's grounded sweep and both of
our own searches agree: no text-to-motion node, template, or partner API; the `3d/*` category
is splat-only; no video→3D-motion lift exists Cloud-side, and 2D `POSE_KEYPOINT`/depth
outputs do not satisfy the slot's contract (3D skeletal animation Blender can retarget onto
the 22-bone rig).

**R6 — the consult's interim suggestion is REJECTED as out of frame.** It recommended
driving SLOT 2 "from a rig-rendered performance you author/retarget in Blender (hand-key or
a self-owned clip)" for the first shot. That is the first dead reading of E08 returning
through a side door: the confirmed frame is both-stages-generative, no hand-authored motion.
The agent was never told E08's dispatch history and cannot be faulted for it; the advisor's
job is exactly this rejection. The frame re-opens only by the Director's word, never by a
consult's convenience.

**R7 — the next action is the SLOT-1 licence pass** (web fetches, zero credits): per
candidate, retrieve the actual LICENSE of the specific release **and** of the tier that
usually gates this field — the body model and the training data. Candidates from the
consult, direct text-to-motion: MDM, MotionGPT, MoMask, T2M-GPT, OmniControl/OMG.
Video→3D-motion lift: WHAM, TRAM, GVHMR, 4D-Humans/HMR2.0, SMPLer-X. The gating tier:
SMPL/SMPL-X body-model licences, AMASS, HumanML3D. One advisor-added candidate for the pass:
**MediaPipe Pose** (Apache-family, monocular 3D world landmarks, no SMPL dependency) — a
possible clean closure of sub-shape (b) whose costs are a landmark→22-bone solver we would
have to commission and an unmeasured quality ceiling on dance-grade motion. Expectation
recorded honestly: the research body-model tier is likely NO for most of the field; the pass
exists to find the exception or to record the absence, either being a full result.

**R8 — adopted for the spec rewrite:** cross-shot identity rides a fixed set of GLB
reference renders (+ `character_mask`) — the multi-shot lever; the continuation sockets are
chunked extension of one shot (tooltip-verified), not a cross-shot memory. Credit figures
from the consult stay SPECULATION; E02's measured 4 credits/generation is the planning
number until re-measured on the Animate graph.

## Map updates made this round

1. ComfyUI core node code: GPL-3.0 fetched and filed (Services and tools) — resolves the
   ASSUMED-from-category row for the core Wan conditioning nodes.
2. Preprocessor section: the served-Animate-template contamination recorded as trap #3.
3. UNVERIFIED table: "Wan Animate 2" and SCAIL-2 rows added, both treated NO.

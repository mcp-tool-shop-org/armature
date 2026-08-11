# Comfy Agent consult #6 — filling the two generative slots of the first shot

**From:** the armature advisor seat, 2026-08-11 · **Relay:** the Director carries this brief to
the Comfy Agent and returns its answer · **Trigger:** the Director confirmed E08's frame —
generative at both ends, with the rigged character load-bearing in the middle · **Numbering:**
this file continues the brief series in this repo (01, 3, 5 → 6); the licence map also cites a
brief-less round as consult #7 (2026-08-10), so the series is not chronological — the file
series is what this number tracks.

---

## Context — the confirmed frame, then what we hold

armature is a previz-to-video pipeline: a canonical character GLB is staged in **headless
Blender 5.2** and its renders drive video generation on Comfy Cloud. The Director has confirmed
the first product shot's frame, and it is **generative at both ends**: a prompt goes into a
motion model, the generated motion lands on the character's **own rigged skeleton**, and a
video model paints him performing it. Nobody hand-keys anything. The rig is the socket the
generated performance plugs into — the character (22-bone skeleton, mesh we own) receives the
motion, and from that rigged geometry we can render **any** driving or control form ourselves:
pose sticks in a convention you name, depth, masks, or a full CG render of the character
performing, from any angle. The shot: **the character dances in a crowded bar, ~4 seconds.**
It exists to show three things — the character in action; the **same** character available
across multiple shots; and how well the **scene** (bar, crowd, light) arrives from the text
prompt around a GLB-anchored character.

What we hold, measured: a Comfy Cloud workspace with saved Wan 2.1 VACE graphs (an
832×480×65-frame route already checked for frame legality); the rigged character GLB; headless
Blender. Licence gate, non-negotiable: **no non-commercial model, weight, preprocessor or code
dependency anywhere in the pipeline** — CC-BY-NC / research-only banned outright, UNVERIFIED
treated as NO. **Do not rule licences for us** — give exact model/file/version names and the
URL of the licence document where you can see one; the ruling is ours.

## Already verified or measured — do not re-derive

| item | state |
|---|---|
| Wan 2.1 T2V / VACE · Wan 2.2 T2V / I2V · Wan2.2-Fun-A14B-Control · Wan2.2-VACE-Fun-A14B · **Wan2.2-Animate-14B** (model weights) | licence-mapped Apache-2.0, commercial YES |
| `WanAnimateToVideo` core node | in our map as ASSUMED-from-category; licence row not yet retrieved — one target of this consult |
| `ComfyUI-WanAnimatePreprocess` detector tier (ViTPose / DWPose / YOLO weights) | UNVERIFIED = NO in our map — and unnecessary for us: we render pose from rigged geometry we own, no detector in the pipeline |
| Kling · MiniMax · Seedance partner terms | UNVERIFIED = NO until their terms are retrieved (fetch attempts failed; recorded in our map) |
| LTX-2 | CONDITIONAL (revenue-capped community licence) — usable only by a Director decision |
| Our own catalog look, 2026-08-11 | templates seen: `video_wan2_2_14B_animate` · `video_wan_animate2` ("Wan Animate 2: Motion Transfer", described as needing no pose extraction) · `video_wan21_scail2_character_replacement` (+ `_int8`) · `video_ltx2_pose_to_video` · `api_kling_motion_control` / `3` · `video_minimax_h3_r2v` · `api_seedance2_0_r2v`. Core node `WanAnimateToVideo` (lean inputs include `continue_motion_max_frames`, `video_frame_offset`). No text-to-motion generator surfaced in our searches. |
| Our local model KB (119 models, 9 domains) | holds **no text-to-motion entry** — measured tonight |

## The two slots, stated precisely

**SLOT 1 — the motion generator (the open half): prompt → skeletal motion.**
The output must terminate as **3D skeletal animation that local Blender can retarget onto a
22-bone humanoid GLB rig** — BVH, FBX, glTF animation, an SMPL(-X) sequence, or a documented
joint-rotation format. A route that only ever produces a 2D pose video does **not** fill this
slot: the rig is load-bearing (identity, any-angle renders, and the multi-shot goal all live
on it). Two admissible sub-shapes: **(a)** direct text-to-motion; **(b)** text-to-video, then
a video-to-3D-motion lift (mocap-from-video), if every stage is clean.

**SLOT 2 — the performer (the promising half): the performance on his rig → footage.**
Input we can produce: anything renderable from rigged geometry — pose-stick sequences in a
convention you name, depth, masks, or a full CG render of the character performing in a void
or a blocked scene. Candidates our catalog look surfaced: Wan2.2-Animate-14B
(`video_wan2_2_14B_animate` / `WanAnimateToVideo`), "Wan Animate 2" (`video_wan_animate2`),
SCAIL-2, Wan2.2-Fun-A14B-Control — and our saved Wan VACE route as the fallback.

## The questions, ranked

**Q0 — calibration (answer first, briefly).** Which template(s) currently serve Wan 2.2
Animate 14B, and through which core node class does the served graph condition? *(We hold
this answer from our own catalog look; it is this round's cheap-verification anchor.)*

**Q1 — SLOT 1 on Comfy Cloud.** Does anything in the catalog — node pack, template, or
partner API — generate **skeletal motion from a text prompt**? Exact names as saved. If the
direct form does not exist: what is the nearest catalog machinery for sub-shape (b) —
video-to-3D-motion (mocap-from-video, SMPL estimation) — and what does the commercially-clean
OSS field **outside** Cloud offer today for text-to-motion (exact project names, versions,
repos; we fetch the licences)? If the honest answer is "nothing clean exists," say that
plainly — it is a full answer, and the route then leans on sub-shape (b) or on SLOT 2 routes
whose driving input we can produce another way.

**Q2 — SLOT 2 mechanism, per candidate.** For Wan2.2-Animate-14B, "Wan Animate 2", SCAIL-2,
and Wan2.2-Fun-A14B-Control: **(a)** the full input schema — which inputs are required vs
optional (reference image · driving/pose video · face video · background video · character
mask · text prompt); **(b)** the exact form the driving input takes, and whether a sequence
**we render from rigged geometry** (pose sticks in the model's expected convention, or a CG
render of the character performing) is a first-class driving input — or whether the served
graph assumes its own detector stage; **(c)** **where the scene comes from** — with identity
on the reference, can the text prompt paint the crowded bar, or is the background inherited
from the reference or driving input? Clause (c) decides the shot.

**Q3 — identify the variants.** What exactly is "Wan Animate 2" as served — model name,
version, weight files, relation to Wan2.2-Animate-14B, and the URL of its licence document?
Same for SCAIL-2. Our gate checks the exact variant, never the family.

**Q4 — the multi-shot question.** With a fixed set of reference renders of one character,
what does each Q2 candidate offer for keeping the **same** character across separate
submissions — and what do `continue_motion_max_frames` / `video_frame_offset` on
`WanAnimateToVideo` enable (continuation of one shot? chaining shots?)? Anything else in the
catalog built for cross-shot character consistency?

**Q5 — legality and cost.** Per Q2 candidate: legal resolution buckets and frame-count forms
for a ~4 s clip, and rough credit cost per generation at 480p and 720p.

**Q6 — recommendation.** Rank the routes that appear clean under our gate for **this** shot
(dance, crowded bar, scene from prompt, character from rig). Then, per our calibration
protocol, close with **one cheap, checkable claim** we can verify locally before acting on
anything expensive.

## Answer format requested

Q0 first. Then a per-candidate table covering Q2 / Q3 / Q5, prose for Q1 / Q4, one ranked
recommendation, the calibration claim last. Exact names as saved in the catalog — named models
are not substitutable. Anything uncertain is marked SPECULATION rather than smoothed.
Deviations from the questions, listed at the top.

## Standing rules (abbreviated — this is a question brief, not a build order)

No builds, no tab creation or mutation, no workflow edits, no generations. This round spends
nothing. Licence verdicts are ours; bring documents, not conclusions.

# Comfy Agent consult #7 — the answer, calibrated and ruled

**Advisor ruling, 2026-08-12.** Brief: [comfy-consult-7-brief.md](comfy-consult-7-brief.md).
Question round; the agent confirmed zero spend and zero mutations, and its deviations were
the honest kind — a negative result reported instead of a detour (no Wan prompt-travel
exists), and "I cannot quote the guide" instead of a paraphrase of a document it cannot see.

## Calibration — five node claims, all verified against the live catalog

| claim | verification | verdict |
|---|---|---|
| `ConditioningSetTimestepRange` = {conditioning, start, end} floats 0–1 — **denoise-schedule window, not video time** | `get_node`: schema exact | **PASS — and the mechanism distinction is confirmed from schema** |
| `ConditioningSetAreaPercentageVideo` exists, core, with `temporal` and `z` axes | `get_node`: core pack, all eight sockets as claimed | **PASS — the served video-time text primitive is real** |
| `WanCameraEmbedding` with the nine-pose enum + speed + intrinsics | `get_node`: enum verbatim (Static / Pan ×4 / Zoom ×2 / ACW / CW); **pack: core**; defaults literally 832×480×81 | **PASS** |
| `WanCameraImageToVideo` consuming the embedding + start image | `get_node`: core; optional `start_image` + `camera_conditions` | **PASS** |
| `WanFirstLastFrameToVideo` optional start/end image + clip-vision pairs | `get_node`: exact | **PASS** |

Five for five, socket for socket — against consult #6's one phantom node class. Channel
trust updated accordingly: this round's existence claims held; the standing rule (no node
enters the record unverified) stays regardless.

**The agent's proposed local check is DECLINED, with the reason on the record:** it
suggested wiring a timestep-range split on a scratch tab and running one clip to prove the
denoise-time claim. The claim is **schema-decidable** — `start`/`end` are unit-interval
floats on the conditioning, the standard denoise-window primitive — and this ruling's own
`get_node` read settles it deterministically. A generation would have measured the behavior
of a mechanism already ruled the wrong tool: zero information value, one clip's GPU time,
and a tab mutation. Declined.

## R1 — the timeline law, folded

**Denoise time is not video time.** `ConditioningSetTimestepRange` partitions *which
sampling steps* a prompt drives (structure vs detail across the whole clip) and never
appears in a narration design here. The served video-time text primitive is
**`ConditioningSetAreaPercentageVideo`** (core; spatial box + `temporal`/`z` window +
strength, merged via `ConditioningCombine`). Its effectiveness on Wan's DiT is
**unmeasured** — it enters as an experiment, never as a production lever on faith.

## R2 — the narration shelf, adopted (cheapest first)

1. **Beat endpoints — `WanFirstLastFrameToVideo`** (core; sockets verified; zero new
   licence surface). The start and end frames can be **authored from the GLB**: pose the
   rig at beat-start and beat-end in previz, render both, and let the model perform the
   beat between. The most GLB-native narration mechanism that exists — previz decides the
   beats, the model performs them.
2. **Cross-clip chaining with a different prompt per chunk** — `continue_motion` on the
   driven route, last-frame→start-frame on the free route; the identity reference stays
   fixed every hop, only the beat clause moves. The named chaining risks ride as measured
   quantities when this lever runs: per-hop tone drift, identity erosion, seam velocity
   reset (`continue_motion` is the seam mitigation and exists for exactly this).
3. **Video-time text scheduling** — `ConditioningSetAreaPercentageVideo` +
   `ConditioningCombine` (core). "Bartender-text scoped to the right third, frames 20–50"
   is expressible; whether Wan honors it cleanly is its own cheap probe first (R1).
4. **Camera direction — `WanCameraEmbedding` + `WanCameraImageToVideo`** (both **core**
   nodes under the existing ComfyUI-core GPL row; the **Fun-Camera aux weights fetched
   this ruling: Apache-2.0** — map row landed). Text-free, enum + speed, defaults at our
   exact shape, pairs directly with the no-control route's GLB start frame. The highest
   control-per-effort lever on the shelf now that its licence is clear.
5. **Set-hold anchors** — VACE reference channel, Animate `background_video`, the I2V
   start frame — orthogonal; layer under any of the above.

## R3 — the negative results, adopted as fences

No Wan-native prompt-travel node exists — the ADE_* scheduling family is the AnimateDiff
sampler ecosystem and never attaches to a Wan route here regardless of its licence. The
only `Video Extension` template is a partner API (Grok) — off-gate. `FL_*` Fill-pack
duplicates are WIP — the core nodes are the route. And **no count-control node exists**:
scene population remains prompt + negative + seed, governed by the two-seed rule.

## R4 — map rows and open fetches

**Wan2.2-Fun-A14B-Control-Camera: Apache-2.0, fetched 2026-08-12** — row landed, with the
honest note that this card is silent on output rights (the base-family output clause is not
on it; Comfy Cloud's ToS ownership row governs our generations service-side). Unchanged and
unverified-therefore-NO: `WanVaceAdvanced`, KJNodes, the ADE pack, `FL_*` WIP. **Open fetch,
owner = advisor at narration-spec time:** the official Wan prompting guide's
temporal-ordering prose (the agent could not quote it and honestly said so).

## R5 — queue implication

The shelf is E12+ material, behind E11's probe. The natural first narration experiment is
**beat endpoints** (lever 1 — cheapest, most deterministic, and it makes previz the
storyteller); **camera embedding** (lever 4) is second now that its licence is clear, and
it upgrades the no-control route directly. The Director orders the shelf when E11's sheet
lands.
